from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Tuple

from .utils import join_headers, to_bytes


STATUS_REASONS: Dict[int, str] = {
    200: "OK",
    201: "Created",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    304: "Not Modified",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    411: "Length Required",
    413: "Payload Too Large",
    414: "URI Too Long",
    415: "Unsupported Media Type",
    500: "Internal Server Error",
}


def _http_date() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%a, %d %b %Y %H:%M:%S GMT")


class Response:
    def __init__(self, status: int = 200, headers: Dict[str, str] | None = None, body: bytes | str = b"") -> None:
        self.status = status
        self.headers = {"Date": _http_date(), "Server": "shs/0.1"}
        if headers:
            self.headers.update(headers)
        self.body = to_bytes(body)
        if self.body and "Content-Length" not in self.headers:
            self.headers["Content-Length"] = str(len(self.body))

    def start_line(self) -> bytes:
        reason = STATUS_REASONS.get(self.status, "")
        return f"HTTP/1.1 {self.status} {reason}\r\n".encode("iso-8859-1")

    def to_bytes(self) -> bytes:
        return self.start_line() + join_headers(self.headers) + self.body


def text(body: str, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> Response:
    data = body.encode("utf-8")
    return Response(status, {"Content-Type": content_type, "Content-Length": str(len(data))}, data)


def json(body: str, status: int = 200) -> Response:
    return text(body, status, content_type="application/json; charset=utf-8")


def not_found() -> Response:
    return text("Not Found", 404)


def method_not_allowed() -> Response:
    return text("Method Not Allowed", 405)


def bad_request(msg: str = "Bad Request") -> Response:
    return text(msg, 400)


def internal_error() -> Response:
    return text("Internal Server Error", 500)

