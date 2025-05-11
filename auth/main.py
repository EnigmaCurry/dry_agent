import pyotp
import base64
from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import PlainTextResponse, RedirectResponse, HTMLResponse
from itsdangerous import Signer, BadSignature
import os
import qrcode
from rich.console import Console
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
from pathlib import Path

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

SECRET_FILE = "/data/secret/secret.txt"
TOKEN_FILE = "/data/token/current_token.txt"
OTP_COOKIE_NAME = "dry_otp"
OTP_COOKIE_VALUE = "valid"
OTP_COOKIE_PATH = "/"
OTP_COOKIE_MAX_AGE = 86400 * 7  # 7 days
AUTH_COOKIE_NAME = "dry_agent_auth"

PUBLIC_HOST = os.environ.get("PUBLIC_HOST", "127.0.0.1")
PUBLIC_PORT = os.environ.get("PUBLIC_PORT", "8002")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
signer: Signer = None  # Will be set on startup
secret_key: bytes = None
current_token: str = ""


def get_forwarded_ip(request: Request) -> str:
    # X-Forwarded-For may contain multiple IPs; the first is the real client
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host  # fallback


@app.middleware("http")
async def log_ip_middleware(request: Request, call_next):
    ip = get_forwarded_ip(request)
    logger.info(f"Request from IP: {ip} {request.method} {request.url.path}")
    response = await call_next(request)
    return response


limiter = Limiter(key_func=get_forwarded_ip)
app.state.limiter = limiter


def load_or_create_secret_key(path: str = SECRET_FILE) -> bytes:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read().strip()
    key = os.urandom(32)
    with open(path, "wb") as f:
        f.write(key)
    return key


class TokenFileEventHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def on_modified(self, event):
        if os.path.abspath(event.src_path) == os.path.abspath(TOKEN_FILE):
            self.loop.call_soon_threadsafe(load_token_from_file)


def load_token_from_file():
    global current_token
    try:
        with open(TOKEN_FILE, "r") as f:
            current_token = f.read().strip()
            logger.info(f"Updated current_token: {current_token}")
    except Exception as e:
        logger.error(f"Failed to read token file: {e}")
        current_token = ""


@app.on_event("startup")
async def startup():
    global signer, secret_key
    secret_key = load_or_create_secret_key()
    signer = Signer(secret_key)

    loop = asyncio.get_event_loop()
    load_token_from_file()
    event_handler = TokenFileEventHandler(loop)
    observer = Observer()
    observer.schedule(event_handler, path=str(Path(TOKEN_FILE).parent), recursive=False)
    observer.start()
    app.state.token_file_observer = observer


@app.on_event("shutdown")
async def stop_token_file_observer():
    observer = getattr(app.state, "token_file_observer", None)
    if observer:
        observer.stop()
        observer.join()


def get_totp():
    # Derive a fixed TOTP secret from master key
    secret = base64.b32encode(secret_key[:10])  # 80 bits
    return pyotp.TOTP(secret)


def display_totp_qr_in_terminal(label="dry-agent", issuer="dry-agent"):
    secret_key = load_or_create_secret_key()
    secret_key = base64.b32encode(secret_key[:10]).decode()

    totp = pyotp.TOTP(secret_key)
    uri = totp.provisioning_uri(name=label, issuer_name=issuer)

    # Generate the QR code
    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)

    # Print to terminal
    console = Console()
    console.print("\n[bold green]Scan this QR code with your TOTP app:[/bold green]\n")
    qr.print_ascii(invert=True)  # or use print_tty() for fallback
    console.print(f"\nManual Entry Secret: [bold yellow]{secret_key}[/bold yellow]\n")

    return secret_key  # return so you can persist or sign it if needed


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


@app.get("/auth")
async def auth(request: Request):
    """
    Traefik ForwardAuth middleware endpoint
    """
    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if not auth_cookie:
        return RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp/logout", status_code=302
        )
    elif auth_cookie != current_token:
        return RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp/logout", status_code=302
        )

    otp_cookie = request.cookies.get(OTP_COOKIE_NAME)
    if not otp_cookie:
        return RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp", status_code=302
        )
    try:
        value = signer.unsign(otp_cookie).decode()
        if value == OTP_COOKIE_VALUE:
            return PlainTextResponse("Authorized", status_code=200)
    except BadSignature:
        pass

    return RedirectResponse(
        url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp", status_code=302
    )


@app.post("/totp/verify")
@limiter.limit("2/minute")
async def totp_verify(request: Request, code: str = Form(...)):
    auth_cookie = request.cookies.get(AUTH_COOKIE_NAME)
    if not auth_cookie:
        return RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp/logout", status_code=302
        )
    elif auth_cookie != current_token:
        return RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp/logout", status_code=302
        )

    otp_cookie = request.cookies.get(OTP_COOKIE_NAME)
    if otp_cookie:
        try:
            value = signer.unsign(otp_cookie).decode()
            if value == OTP_COOKIE_VALUE:
                response = RedirectResponse(
                    url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/", status_code=302
                )
                return response
        except BadSignature:
            response = RedirectResponse(
                url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/", status_code=302
            )
            response.delete_cookie(OTP_COOKIE_NAME, path=OTP_COOKIE_PATH)
            return response
    else:
        totp = get_totp()
        if totp.verify(code):
            signed = signer.sign(OTP_COOKIE_VALUE.encode()).decode()
            is_https = request.headers.get("x-forwarded-proto") == "https"
            response = RedirectResponse(
                url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/", status_code=302
            )
            response.set_cookie(
                key=OTP_COOKIE_NAME,
                value=signed,
                httponly=True,
                path=OTP_COOKIE_PATH,
                max_age=OTP_COOKIE_MAX_AGE,
                secure=is_https,
                samesite="Lax",
            )
            return response

    return RedirectResponse(
        url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/totp", status_code=302
    )


@app.get("/totp/logout")
async def totp_logout(response: Response):
    response = RedirectResponse(
        url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/login", status_code=302
    )
    response.delete_cookie(OTP_COOKIE_NAME, path=OTP_COOKIE_PATH)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@app.get("/totp", response_class=HTMLResponse)
async def totp_form():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>TOTP Login - dry_agent</title>
      <style>
        body {
          margin: 0;
          padding: 0;
          background-color: #121212;
          color: #f0f0f0;
          font-family: Arial, sans-serif;
          overflow: hidden;
        }
        .section {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
        }
        .container {
          background-color: #1e1e1e;
          padding: 2rem;
          border-radius: 8px;
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
          width: 360px;
        }
        h1.title {
          text-align: center;
          margin-bottom: 1.5rem;
          font-size: 1.8rem;
        }
        input[type="text"] {
          width: 100%;
          padding: 0.75rem 1rem;
          margin-bottom: 1rem;
          border: 1px solid #444;
          border-radius: 4px;
          background-color: #333;
          color: #fff;
          font-size: 1rem;
          box-sizing: border-box;
        }
        label.label {
          margin-bottom: 0.5rem;
          display: block;
        }
        button {
          width: 100%;
          padding: 1rem;
          background-color: #007BFF;
          border: none;
          border-radius: 4px;
          font-size: 1.2rem;
          color: #fff;
          cursor: pointer;
          transition: background-color 0.2s ease-in-out;
        }
        button:hover {
          background-color: #0056b3;
        }
        .notification.is-danger {
          background-color: #ff4d4d;
          padding: 0.75rem;
          margin-bottom: 1rem;
          border-radius: 4px;
          text-align: center;
        }
      </style>
    </head>
    <body>
      <section class="section">
        <div class="container">
          <h1 class="title">Authenticate with TOTP</h1>
          <form method="post" action="/totp/verify" autocomplete="off">
            <div class="field">
              <label class="label">Verify 6 Digit TOTP Code</label>
              <div class="control">
                <input type="text" name="code" placeholder="123456" required autocomplete="one-time-code" autofocus>
              </div>
            </div>
            <div class="field">
              <div class="control">
                <button type="submit">Verify</button>
              </div>
            </div>
          </form>
        </div>
      </section>
    </body>
    </html>
    """


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="dry-agent-auth server / QR tool")
    parser.add_argument(
        "--qr",
        action="store_true",
        help="Print TOTP QR code to terminal instead of starting the server",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the FastAPI server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(PUBLIC_PORT),
        help="Port to bind the FastAPI server",
    )

    args = parser.parse_args()

    if args.qr:
        display_totp_qr_in_terminal()
    else:
        uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
