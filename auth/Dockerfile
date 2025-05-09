FROM python:3.11-slim

WORKDIR /app
COPY main.py .

RUN pip install fastapi uvicorn itsdangerous pyotp qrcode rich \
    python-multipart slowapi watchdog

VOLUME ["/data"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
