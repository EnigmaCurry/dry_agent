import re
from typing import List, Tuple

# ── URL pattern ──────────────────────────────────────────────────────────────
#  • http:// or https://
#  • optional user:pass@ , sub‑domains, ports, query‑strings, fragments, etc.
#  • OR a bare www.example.com form
_URL_RE = re.compile(
    r"""(?xi)                     # x = verbose, i = ignore‑case
    (                             # 1) full match
      https?://                   #    http:// or https://
      [^\s<>"]+                   #    up‑to first whitespace/angle/quote
      |
      www\.[^\s<>"]+              # 2) or bare www.*
    )
    """
)


def strip_urls(text: str, collapse_whitespace: bool = True) -> Tuple[List[str], str]:
    """
    Extract all URLs from *text* and return (urls, text_without_urls).

    Parameters
    ----------
    text : str
        Input string.
    collapse_whitespace : bool, default True
        If True, replace runs of 2+ whitespace characters that arise
        after stripping with a single space and trim leading/trailing
        whitespace.

    Examples
    --------
    >>> txt = "See https://example.com/docs and http://foo.tld?x=1 ."
    >>> strip_urls(txt)
    (['https://example.com/docs', 'http://foo.tld?x=1'],
     'See and .')
    """
    urls = _URL_RE.findall(text)
    cleaned = _URL_RE.sub("", text)

    if collapse_whitespace:
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    return urls, cleaned
