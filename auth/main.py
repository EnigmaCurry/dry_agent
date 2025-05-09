import pyotp
import base64
from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import PlainTextResponse, RedirectResponse, HTMLResponse
from itsdangerous import Signer, BadSignature
import os
import qrcode
from rich.console import Console

SECRET_FILE = "/data/secret_key.txt"
COOKIE_NAME = "dry_otp"
COOKIE_VALUE = "valid"
COOKIE_PATH = "/"
COOKIE_MAX_AGE = 86400 * 7  # 7 days

PUBLIC_HOST = os.environ.get("PUBLIC_HOST", "127.0.0.1")
PUBLIC_PORT = os.environ.get("PUBLIC_PORT", "8002")

app = FastAPI()
signer: Signer = None  # Will be set on startup
secret_key: bytes = None


def load_or_create_secret_key(path: str = SECRET_FILE) -> bytes:
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
    global signer, secret_key
    secret_key = load_or_create_secret_key()
    signer = Signer(secret_key)


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


@app.get("/totp", response_class=HTMLResponse)
async def totp_form():
    return """
    <html>
      <head><title>TOTP Login</title></head>
      <body>
        <h1>Authenticate with TOTP</h1>
        <form method="post" action="/totp/verify">
          <label for="code">Code:</label>
          <input type="text" id="code" name="code" required>
          <button type="submit">Verify</button>
        </form>
      </body>
    </html>
    """


@app.post("/totp/verify")
async def totp_verify(request: Request, code: str = Form(...)):
    totp = get_totp()
    if totp.verify(code):
        signed = signer.sign(COOKIE_VALUE.encode()).decode()
        is_https = request.headers.get("x-forwarded-proto") == "https"
        response = RedirectResponse(
            url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/", status_code=302
        )
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
    return PlainTextResponse("Invalid TOTP", status_code=401)


@app.get("/totp/logout")
async def totp_logout(response: Response):
    response = RedirectResponse(
        url=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/login", status_code=302
    )
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
    return response


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
