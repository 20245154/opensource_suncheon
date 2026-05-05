from __future__ import annotations

import os
from typing import Dict, Iterable, Tuple


CRLF = b"\r\n"
HEADER_SEP = b":"


def to_bytes(data: str | bytes) -> bytes:
    if isinstance(data, bytes):
        return data
    return data.encode("iso-8859-1")


def to_str(data: bytes | str) -> str:
    if isinstance(data, str):
        return data
    return data.decode("iso-8859-1", errors="replace")


def normalize_header_name(name: str) -> str:
    return "-".join(part.capitalize() for part in name.strip().split("-"))


def join_headers(headers: Dict[str, str]) -> bytes:
    lines = [f"{normalize_header_name(k)}: {v}" for k, v in headers.items()]
    return ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1")


def safe_join(base: str, path: str) -> str:
    full = os.path.normpath(os.path.join(base, path.lstrip("/")))
    if os.path.commonpath([os.path.abspath(full), os.path.abspath(base)]) != os.path.abspath(base):
        raise ValueError("attempted directory traversal")
    return full


def parse_query_string(path: str) -> Tuple[str, Dict[str, str]]:
    if "?" not in path:
        return path, {}
    p, q = path.split("?", 1)
    params: Dict[str, str] = {}
    for pair in filter(None, q.split("&")):
        if "=" in pair:
            k, v = pair.split("=", 1)
        else:
            k, v = pair, ""
        params[url_decode(k)] = url_decode(v)
    return p, params


def url_decode(s: str) -> str:
    out = bytearray()
    i = 0
    bs = s.encode("utf-8")
    while i < len(bs):
        c = bs[i]
        if c == ord("+"):
            out.append(ord(" "))
            i += 1
        elif c == ord("%") and i + 2 < len(bs):
            try:
                out.append(int(bs[i + 1 : i + 3].decode(), 16))
                i += 3
            except Exception:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return out.decode("utf-8", errors="replace")


def guess_mimetype(path: str) -> str:
    import mimetypes

    typ, _ = mimetypes.guess_type(path)
    return typ or "application/octet-stream"

