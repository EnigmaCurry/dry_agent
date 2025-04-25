#!/usr/bin/env python3
import requests
import os

PUBLIC_HOST = os.environ["PUBLIC_HOST"]
PUBLIC_PORT = os.environ["PUBLIC_PORT"]


def main():
    url = "http://127.0.0.1:8001/admin/generate-auth-token"
    try:
        # Send a POST request
        response = requests.post(url)
        response.raise_for_status()
        print(response.text)  # prints the HTML message from the server
    except Exception as e:
        print("Error during request:", e)
        raise

    # Now read the token from the filesystem.
    try:
        with open("current_token.txt", "r") as f:
            token_from_file = f.read().strip()
        print()
        print(f"https://{PUBLIC_HOST}:{PUBLIC_PORT}/login#{token_from_file}")
    except Exception as e:
        print("Error reading token file:", e)
        raise


if __name__ == "__main__":
    main()
