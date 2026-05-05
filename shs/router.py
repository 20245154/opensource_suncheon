from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .request import Request
from .response import Response, method_not_allowed, not_found


Handler = Callable[[Request, Dict[str, str]], Response]


@dataclass
class Route:
    method: str
    pattern: List[Tuple[str, Optional[str]]]  # (literal or None, param name)
    handler: Handler


def compile_pattern(path: str) -> List[Tuple[str, Optional[str]]]:
    parts = []
    for seg in filter(None, path.split("/")):
        if seg.startswith("{") and seg.endswith("}"):
            parts.append(("", seg[1:-1]))
        else:
            parts.append((seg, None))
    return parts


class Router:
    def __init__(self) -> None:
        self.routes: List[Route] = []

    def add(self, method: str, path: str, handler: Handler) -> None:
        self.routes.append(Route(method.upper(), compile_pattern(path), handler))

    def match(self, method: str, path: str) -> Tuple[Optional[Handler], Dict[str, str], bool]:
        allowed: List[str] = []
        for r in self.routes:
            params: Dict[str, str] = {}
            if self._match_path(r.pattern, path, params):
                if r.method == method.upper():
                    return r.handler, params, True
                allowed.append(r.method)
        return (None, {}, len(allowed) > 0)

    def _match_path(self, pattern: List[Tuple[str, Optional[str]]], path: str, params: Dict[str, str]) -> bool:
        pseg = list(filter(None, path.split("/")))
        if len(pseg) != len(pattern):
            return False
        for (lit, name), seg in zip(pattern, pseg):
            if name is not None:
                params[name] = seg
            elif lit != seg:
                return False
        return True

    def dispatch(self, req: Request) -> Response:
        handler, params, found = self.match(req.method, req.path)
        if handler:
            return handler(req, params)
        return method_not_allowed() if found else not_found()

