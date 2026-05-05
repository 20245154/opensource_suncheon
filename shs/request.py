from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Request:
    method: str
    target: str
    path: str
    query: Dict[str, str]
    version: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    client_addr: Optional[str] = None

    def header(self, name: str, default: str | None = None) -> Optional[str]:
        key = "-".join(part.capitalize() for part in name.split("-"))
        return self.headers.get(key, default)

