#!/usr/bin/env python3
import requests
import os
import secrets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_HOST = os.environ["PUBLIC_HOST"]
PUBLIC_PORT = os.environ["PUBLIC_PORT"]
TOKEN_FILE = "/data/token/current_token.txt"

# Client cert (and its key) for mTLS
CLIENT_CERT = (
    "/certs/dry-agent_App.crt",
    "/certs/dry-agent_App.key",
)
CA_BUNDLE = "/certs/dry-agent-root.crt"


def main():
    if not os.path.isfile(CLIENT_CERT[0]):
        raise RuntimeError("Missing client cert")
    elif not os.path.isfile(CLIENT_CERT[1]):
        raise RuntimeError("Missing client key")
    elif not os.path.isfile(CA_BUNDLE):
        raise RuntimeError("Missing CA bundle")

    url = "https://127.0.0.1:8001/login"
    response = requests.get(url, cert=CLIENT_CERT, verify=CA_BUNDLE)

    url = "https://127.0.0.1:8001/admin/generate-auth-token"
    try:
        # Send a POST request
        response = requests.post(url, cert=CLIENT_CERT, verify=CA_BUNDLE)
        response.raise_for_status()
        logger.info(response.text)  # prints the HTML message from the server
    except Exception as e:
        logger.info(f"Error during request:{e} - {e.response.text}")
        raise

    # Now read the token from the filesystem.
    try:
        with open(TOKEN_FILE, "r") as f:
            token_from_file = f.read().strip()
        q = secrets.token_urlsafe(4)
        print(f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/login?q={q}#{token_from_file}")
    except Exception as e:
        logger.info(f"Error reading token file: {e}")
        raise


if __name__ == "__main__":
    main()
