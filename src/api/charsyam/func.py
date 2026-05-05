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


def minus(req: Request, params: Dict[str, str]) -> Response | Dict[str, int | str]:
    operands = _read_operands(req)
    if isinstance(operands, Response):
        return operands

    a, b = operands
    return _result("minus", a, b, a - b)


def multiply(req: Request, params: Dict[str, str]) -> Response | Dict[str, int | str]:
    operands = _read_operands(req)
    if isinstance(operands, Response):
        return operands

    a, b = operands
    return _result("multiply", a, b, a * b)


def divide(req: Request, params: Dict[str, str]) -> Response | Dict[str, float | int | str]:
    operands = _read_operands(req)
    if isinstance(operands, Response):
        return operands

    a, b = operands
    if b == 0:
        return bad_request("b must not be 0")
    return _result("divide", a, b, a / b)


def _read_operands(req: Request) -> Tuple[int, int] | Response:
    try:
        return int(req.query["a"]), int(req.query["b"])
    except KeyError:
        return bad_request("a and b query parameters are required")
    except ValueError:
        return bad_request("a and b must be integers")


def _result(operation: str, a: int, b: int, result: int | float) -> Dict[str, int | float | str]:
    return {
        "user_id": "charsyam",
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
    }
