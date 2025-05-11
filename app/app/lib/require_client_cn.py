from functools import wraps
from typing import Set
import logging
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


def require_client_cn(allowed_cns: Set[str]):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(request: Request, *args, **kwargs):
            transport = request.scope.get("transport")
            if not transport:
                logger.debug("No transport in scope; keys=%r", list(request.scope))
                raise HTTPException(401, "Unauthorized - no TLS transport")

            ssl_obj = transport.get_extra_info("ssl_object")
            if not ssl_obj:
                logger.debug("No ssl_object on transport: %r", transport)
                raise HTTPException(401, "Unauthorized - TLS cert required")

            cert = ssl_obj.getpeercert()
            # extract CN exactly like before…
            subject = cert.get("subject", ())
            cn = None
            for rdn in subject:
                for name, val in rdn:
                    if name.lower() == "commonname":
                        cn = val
                        break
                if cn:
                    break

            if cn not in allowed_cns:
                logger.debug("CN %r not allowed (%r)", cn, allowed_cns)
                raise HTTPException(403, f"Forbidden: CN={cn}")

            return await fn(request, *args, **kwargs)

        return wrapper

    return decorator
