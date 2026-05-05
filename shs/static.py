from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from .request import Request
from .response import Response, not_found
from .utils import guess_mimetype, safe_join


def http_date(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def serve_file(req: Request, base_dir: str, path: Optional[str] = None) -> Response:
    subpath = path if path is not None else req.path
    try:
        full = safe_join(base_dir, subpath)
    except ValueError:
        return not_found()
    if os.path.isdir(full):
        full = os.path.join(full, "index.html")
    if not os.path.exists(full) or not os.path.isfile(full):
        return not_found()
    size = os.path.getsize(full)
    mime = guess_mimetype(full)
    with open(full, "rb") as f:
        data = f.read()
    headers = {
        "Content-Type": mime,
        "Content-Length": str(size),
        "Last-Modified": http_date(os.path.getmtime(full)),
    }
    return Response(200, headers, data)

