from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
from itsdangerous import Signer, BadSignature
import os

SECRET_FILE = "/data/secret_key.txt"
COOKIE_NAME = "dry_auth"
COOKIE_VALUE = "valid"
COOKIE_PATH = "/"
COOKIE_MAX_AGE = 86400 * 7  # 7 days

PUBLIC_HOST = os.environ.get("PUBLIC_HOST", "127.0.0.1")
PUBLIC_PORT = os.environ.get("PUBLIC_PORT", "8002")

app = FastAPI()
signer: Signer = None  # Will be set on startup


def load_or_create_secret_key(path: str) -> bytes:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read().strip()
    key = os.urandom(32)
    with open(path, "wb") as f:
        f.write(key)
    return key


@app.on_event("startup")
async def setup_signer():
    global signer
    key = load_or_create_secret_key(SECRET_FILE)
    signer = Signer(key)


@app.get("/auth")
async def auth(request: Request):
    """
    Traefik ForwardAuth middleware endpoint
    """
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp", status_code=302
        )

    try:
        value = signer.unsign(cookie).decode()
        if value == COOKIE_VALUE:
            return PlainTextResponse("Authorized", status_code=200)
    except BadSignature:
        pass

    return RedirectResponse(
        url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp", status_code=302
    )


@app.get("/totp")
async def totp():
    return PlainTextResponse("TOTP", status_code=200)


@app.get("/totp/authenticate")
async def totp_authenticate(request: Request):
    signed = signer.sign(COOKIE_VALUE.encode()).decode()
    is_https = request.headers.get("x-forwarded-proto") == "https"

    response = PlainTextResponse("Authenticated")
    response.set_cookie(
        key=COOKIE_NAME,
        value=signed,
        httponly=True,
        path=COOKIE_PATH,
        max_age=COOKIE_MAX_AGE,
        secure=is_https,
        samesite="Lax",
    )
    return response


@app.get("/totp/logout")
async def totp_logout(response: Response):
    response = PlainTextResponse("Logged out")
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
    return response
