from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request


def get_forwarded_ip(request: Request) -> str:
    # X-Forwarded-For may contain multiple IPs; the first is the real client
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host  # fallback


limiter = Limiter(key_func=get_forwarded_ip)
