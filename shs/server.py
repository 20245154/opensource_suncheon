from __future__ import annotations

import logging
import socket
import threading
import time
from typing import Callable

from .parser import parse_request
from .request import Request
from .response import Response, internal_error


App = Callable[[Request], Response]


def _sendall(conn: socket.socket, data: bytes) -> None:
    view = memoryview(data)
    while view:
        n = conn.send(view)
        view = view[n:]


def handle_connection(conn: socket.socket, addr: tuple[str, int], app: App) -> None:
    log = logging.getLogger("shs.server")
    start = time.monotonic()
    req: Request | None = None
    try:
        req = parse_request(conn, f"{addr[0]}:{addr[1]}")
        res = app(req)
    except Exception:
        log.exception("Error handling request from %s:%s", addr[0], addr[1])
        res = internal_error()
    try:
        _sendall(conn, res.to_bytes())
    finally:
        conn.close()
    duration_ms = (time.monotonic() - start) * 1000.0
    method = req.method if req else "-"
    path = req.path if req else "-"
    clen = res.headers.get("Content-Length") or str(len(res.body))
    log.info("%s %s -> %d %sB from %s:%s in %.2fms", method, path, res.status, clen, addr[0], addr[1], duration_ms)


def serve(host: str, port: int, app: App) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(128)
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_connection, args=(conn, addr, app), daemon=True)
            t.start()
