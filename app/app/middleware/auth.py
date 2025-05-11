# app/middleware/auth.py
import logging
import time
import secrets
from fastapi import Request, Form, HTTPException, Query
from fastapi.responses import (
    RedirectResponse,
    HTMLResponse,
    PlainTextResponse,
    JSONResponse,
)
from starlette.middleware.base import BaseHTTPMiddleware
from dicewarepy import diceware
from app.dependencies import templates
from app.models.events import LogoutEvent
from app.broadcast import broadcast
import os
from app.lib.require_client_cn import require_client_cn
from app.lib.rate_limit import limiter

PUBLIC_HOST = os.environ.get("PUBLIC_HOST", "127.0.0.1")
PUBLIC_PORT = os.environ.get("PUBLIC_PORT", "8123")


def token():
    return "-".join(diceware(10))


# Generate an initial token at startup using 10 diceware words joined by hyphens.
current_token = token()
AUTH_COOKIE_NAME = "dry_agent_auth"
CSRF_COOKIE_NAME = "csrf_token"
TOKEN_FILE = "/data/token/current_token.txt"

logger = logging.getLogger("auth")

ALLOWED_CNS = {
    "dry-agent Bot",
}


# Write the token to a file so it can be retrieved via CLI.
def write_token_to_file(token_value: str):
    with open(TOKEN_FILE, "w") as f:
        f.write(token_value)


# Write the initial token to file.
write_token_to_file(current_token)

# Global rate limiting state (for all clients)
failed_attempt_count = 0
last_failed_time = 0.0
BASE_DELAY = 1.0  # initial delay in seconds
MAX_DELAY = 300.0  # maximum delay (5 minutes)


def record_login_attempt(success: bool = False):
    """Record a login attempt globally. Reset on success; increment on failure."""
    global failed_attempt_count, last_failed_time
    now = time.time()
    if success:
        failed_attempt_count = 0
        last_failed_time = 0.0
    else:
        failed_attempt_count += 1
        last_failed_time = now


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow endpoints that don't require cookies
        # (Some like /admin are still blocked later by Traefik)
        if (
            request.url.path.startswith("/login")
            or request.url.path.startswith("/logout")
            or request.url.path.startswith("/static")
            or request.url.path.startswith("/admin/generate-auth-token")
            or request.url.path.startswith("/admin/get-login-url")
            or request.url.path.startswith("/openapi.json")
            or request.url.path.startswith("/docs")
        ):
            return await call_next(request)

        # Check the cookie value against the current token.
        cookie = request.cookies.get(AUTH_COOKIE_NAME)
        if cookie != current_token:
            # If the request is for an API endpoint, return a JSON error.
            if request.url.path.startswith("/api"):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required. Please log in."},
                )
            # For non-API endpoints, redirect to the login page.
            return RedirectResponse(url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/logout")

        return await call_next(request)


def add_auth_middleware(app):
    app.add_middleware(AuthMiddleware)


async def generate_new_token():
    """Generate a new token, update the global token, and write it to file."""
    global current_token
    new_token = token()
    current_token = new_token
    write_token_to_file(new_token)
    await broadcast(LogoutEvent())
    return new_token


# GET /login endpoint: Redirects to the root page if a valid auth cookie is present, clearing any URL hash.
async def login_get(request: Request):
    # Check for a valid auth cookie.
    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if auth_cookie and auth_cookie == current_token:
        # Return an HTML page that clears the URL fragment and redirects to '/'
        html_content = """
        <html>
          <head>
            <meta charset="utf-8">
            <title>Redirecting...</title>
            <script>
              // Remove the hash from the URL.
              if (window.location.hash) {
                history.replaceState(null, document.title, window.location.pathname + window.location.search);
              }
              // Redirect to the root.
              window.location.href = "/";
            </script>
          </head>
          <body>
            Redirecting to the main page...
          </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    # Otherwise, proceed with rendering the login form.
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_cookie:
        csrf_cookie = secrets.token_urlsafe(16)
    response = templates.TemplateResponse(
        "login.html", {"request": request, "error": None, "csrf_token": csrf_cookie}
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME, value=csrf_cookie, httponly=False, samesite="strict"
    )
    return response


@limiter.limit("5/minute")
async def login_post(request: Request, token: str = Form(...), csrf: str = Form(...)):
    # Retrieve the CSRF token from the cookie.
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_cookie or csrf != csrf_cookie:
        raise HTTPException(status_code=400, detail="Invalid CSRF token.")

    if token == current_token:
        new_token = await generate_new_token()
        record_login_attempt(success=True)
        # Generate a new CSRF token for the new session.
        new_csrf_token = secrets.token_urlsafe(16)
        response = RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/", status_code=302
        )
        response.set_cookie(
            key=AUTH_COOKIE_NAME, value=new_token, httponly=True, samesite="strict"
        )
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=new_csrf_token,
            httponly=False,  # must be readable by client-side code if needed
            samesite="strict",
        )
        return response
    else:
        record_login_attempt(success=False)
        # On failure, re-render the login form with the same CSRF token (from the cookie).
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid token.", "csrf_token": csrf_cookie},
        )


# /logout endpoint: Invalidate the current cookie by generating a new token.
async def logout(request: Request, full: bool = Query(False)):
    await generate_new_token()  # Invalidate any cookie with the old token.
    if full:
        response = RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp/logout", status_code=302
        )
    else:
        response = RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/login", status_code=302
        )
    response.delete_cookie(key=AUTH_COOKIE_NAME)
    return response


@require_client_cn(["dry-agent App", "dry-agent Bot"])
@limiter.limit("2/minute")
async def admin_generate_auth_token(request: Request):
    await generate_new_token()
    return PlainTextResponse(
        f"New token generated. Retrieve it from {TOKEN_FILE} on the filesystem. "
        "All existing clients have been logged out."
    )


@require_client_cn(["dry-agent Bot"])
@limiter.limit("2/minute")
async def admin_get_login_url(request: Request):
    q = secrets.token_urlsafe(4)
    return JSONResponse(
        content={
            "login_url": f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/login?q={q}#{current_token}"
        }
    )


async def get_login_url(request: Request):
    host = request.headers.get("host")
    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if auth_cookie and auth_cookie == current_token:
        q = secrets.token_urlsafe(4)
        return JSONResponse(
            content={"login_url": f"https://{host}/login?q={q}#{current_token}"}
        )
    else:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
