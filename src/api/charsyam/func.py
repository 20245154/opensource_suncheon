from __future__ import annotations

from typing import Dict, Tuple

from shs.request import Request
from shs.response import Response, bad_request


def add(req: Request, params: Dict[str, str]) -> Response | Dict[str, int | str]:
    operands = _read_operands(req)
    if isinstance(operands, Response):
        return operands

    a, b = operands
    return _result("add", a, b, a + b)


def _result(operation: str, a: int, b: int, result: int | float) -> Dict[str, int | float | str]:
    return {
        "user_id": "charsyam",
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
    }
