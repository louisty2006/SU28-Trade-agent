"""HTTP helpers for dataflow fetchers.

macOS Python installs often lack a usable system CA bundle for
``urllib.request.urlopen``.  Use certifi's bundle so HTTPS calls to
StockTwits, Reddit, Arctic Shift, etc. verify correctly.
"""

from __future__ import annotations

import ssl
from typing import Any
from urllib.request import Request, urlopen

import certifi


def urlopen_with_certs(req: Request, timeout: float = 10.0) -> Any:
    """Open ``req`` over HTTPS with certifi's CA bundle."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    return urlopen(req, timeout=timeout, context=ctx)
