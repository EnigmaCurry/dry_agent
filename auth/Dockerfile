FROM python:3.11-slim

WORKDIR /app
COPY main.py .

RUN pip install fastapi uvicorn itsdangerous pyotp qrcode rich \
    python-multipart slowapi watchdog

VOLUME ["/data"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", \
     "--ssl-certfile", "/certs/dry-agent_Auth.crt", \
     "--ssl-keyfile", "/certs/dry-agent_Auth.key", \
     "--ssl-ca-certs", "/certs/dry-agent-root.crt", \
     "--ssl-cert-reqs", "2", "--log-level", "info"]
