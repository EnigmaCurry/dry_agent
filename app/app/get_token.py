#!/usr/bin/env python3
import requests
import os

APP_HOST = os.environ['APP_HOST']
APP_PORT = os.environ['APP_PORT']

def main():
    url = "http://127.0.0.1/admin/generate-auth-token"
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
        print(f"http://{APP_HOST}:{APP_PORT}/login#{token_from_file}")
    except Exception as e:
        print("Error reading token file:", e)
        raise

if __name__ == "__main__":
    main()
