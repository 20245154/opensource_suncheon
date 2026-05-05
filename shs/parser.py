from __future__ import annotations

import socket
from typing import Dict, Tuple

from .request import Request
from .utils import CRLF, parse_query_string, to_str


class BufferedSocket:
    def __init__(self, conn: socket.socket) -> None:
        self.conn = conn
        self.buf = bytearray()

    def recv_into_buf(self, n: int = 4096) -> bool:
        data = self.conn.recv(n)
        if not data:
            return False
        self.buf.extend(data)
        return True

    def read_until(self, marker: bytes) -> bytes:
        while True:
            idx = self.buf.find(marker)
            if idx != -1:
                out = bytes(self.buf[: idx + len(marker)])
                del self.buf[: idx + len(marker)]
                return out
            if not self.recv_into_buf():
                return b""

    def read_exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            if not self.recv_into_buf():
                break
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out


def parse_request_line(line: str) -> Tuple[str, str, str]:
    parts = line.strip().split()
    if len(parts) != 3:
        raise ValueError("invalid request line")
    return parts[0], parts[1], parts[2]


def parse_headers(raw: bytes) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for ln in raw.decode("iso-8859-1").split("\r\n"):
        if not ln:
            continue
        if ":" not in ln:
            continue
        name, value = ln.split(":", 1)
        name = "-".join(part.capitalize() for part in name.strip().split("-"))
        headers[name] = value.strip()
    return headers


def read_headers(buf: BufferedSocket) -> bytes:
    data = buf.read_until(CRLF + CRLF)
    return data[:-4]


def read_chunked_body(buf: BufferedSocket) -> bytes:
    body = bytearray()
    while True:
        line = to_str(buf.read_until(CRLF))
        if not line:
            break
        size_str = line.strip().split(";", 1)[0]
        size = int(size_str, 16)
        if size == 0:
            _ = buf.read_until(CRLF)
            break
        body.extend(buf.read_exact(size))
        _ = buf.read_until(CRLF)
    return bytes(body)


def read_length_body(buf: BufferedSocket, n: int) -> bytes:
    return buf.read_exact(n)


def parse_request(conn: socket.socket, client_addr: str | None = None) -> Request:
    buf = BufferedSocket(conn)
    line = to_str(buf.read_until(CRLF)).strip()
    method, target, version = parse_request_line(line)
    raw_headers = read_headers(buf)
    headers = parse_headers(raw_headers)
    path, query = parse_query_string(target)
    body = b""
    te = headers.get("Transfer-Encoding", "").lower()
    if "chunked" in te:
        body = read_chunked_body(buf)
    elif "Content-Length" in headers:
        body = read_length_body(buf, int(headers["Content-Length"]))
    return Request(method, target, path, query, version, headers, body, client_addr)

