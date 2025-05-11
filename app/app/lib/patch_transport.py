## Get TLS information to stick in the request.
## https://github.com/encode/uvicorn/discussions/2307
from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol

# Keep a reference to the original
_old_on_url = HttpToolsProtocol.on_url


def _patched_on_url(self, url: bytes) -> None:
    # Call the real one (this builds self.scope)
    _old_on_url(self, url)
    # Now stick the transport into the scope
    self.scope["transport"] = self.transport


# Apply the patch
HttpToolsProtocol.on_url = _patched_on_url
