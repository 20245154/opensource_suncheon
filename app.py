from __future__ import annotations

import argparse
import importlib.util
import json as _json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict

from shs.request import Request
from shs.response import Response, json, text
from shs.router import Router
from shs.static import serve_file

try:
    from calculator import calculate
except ModuleNotFoundError as exc:
    if exc.name != "calculator":
        raise

    def calculate(a: int, b: int) -> int:
        return a + b

router = Router()
PROJECT_ROOT = Path(__file__).resolve().parent
STUDENT_API_ROOT = PROJECT_ROOT / "src" / "api"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8081
HOST_ENV = "SHS_HOST"
PORT_ENV = "SHS_PORT"
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SAFE_FUNC_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def hello(req: Request, params: Dict[str, str]) -> Response:
    name = params.get("name", "world")
    return text(f"hello {name}\n")

def add(req: Request, params: Dict[str, str]) -> Response:
    a = params.get("a")
    b = params.get("b")
    result = calculate(int(a), int(b))
    return text(f"result = {result}\n")

def echo(req: Request, params: Dict[str, str]) -> Response:
    payload = {
        "method": req.method,
        "path": req.path,
        "query": req.query,
        "headers": req.headers,
        "body_len": len(req.body),
    }
    return json(_json.dumps(payload))


def health(req: Request, params: Dict[str, str]) -> Response:
    return Response()


def student_api(req: Request, params: Dict[str, str]) -> Response:
    student_id = params.get("id", "")
    func_name = params.get("func_name", "")
    if not SAFE_ID_RE.fullmatch(student_id):
        return text("Invalid student id", 400)
    if not SAFE_FUNC_RE.fullmatch(func_name) or func_name.startswith("_"):
        return text("Invalid function name", 400)

    func_path = STUDENT_API_ROOT / student_id / "func.py"
    if not func_path.is_file():
        return text("Student API not found", 404)

    module = _load_student_module(student_id, func_path)
    target = getattr(module, func_name, None)
    if not callable(target):
        return text("Student API function not found", 404)

    result = target(req, params)
    return _student_api_response(result)


def _load_student_module(student_id: str, func_path: Path) -> Any:
    module_id = student_id.replace("-", "_")
    module_name = f"student_api_{module_id}_func"
    spec = importlib.util.spec_from_file_location(module_name, func_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {func_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _student_api_response(result: Any) -> Response:
    if isinstance(result, Response):
        return result
    if result is None:
        return Response(204)
    if isinstance(result, (dict, list)):
        return json(_json.dumps(result, ensure_ascii=False))
    return text(str(result))


App = Callable[[Request], Response]


def exception_middleware(handler: App) -> App:
    def wrapped(req: Request) -> Response:
        try:
            return handler(req)
        except Exception as exc:
            logging.exception("unhandled error while handling %s %s", req.method, req.path)
            if req.path.startswith("/api/"):
                return _api_exception_response(exc)
            return text("Internal Server Error", 500)

    return wrapped


def _api_exception_response(exc: Exception) -> Response:
    status = getattr(exc, "status", getattr(exc, "status_code", 500))
    if not isinstance(status, int) or status < 400:
        status = 500

    message = str(exc) or "Internal Server Error"
    payload = {
        "error": {
            "type": exc.__class__.__name__,
            "message": message,
        }
    }
    return json(_json.dumps(payload, ensure_ascii=False), status)


"""
Git Lab TODO (충돌 유도 지점)
-----------------------------
- Part 1에서 아래 router.add 인접 라인에 각각 새 라우트를 추가하세요.
- 예시: A → `GET /mul/{a}/{b}`, B → `GET /div/{a}/{b}`
- 가능한 한 `add` 라우트와 가까운 곳(같은 블록)에 배치해 충돌을 유도합니다.
"""

router.add("GET", "/hello/{name}", hello)
router.add("GET", "/echo", echo)
router.add("GET", "/health", health)
router.add("GET", "/add/{a}/{b}", add)
router.add("GET", "/api/v1/{id}/{func_name}", student_api)
router.add("POST", "/api/v1/{id}/{func_name}", student_api)


def _app(req: Request) -> Response:
    base = os.path.join(os.path.dirname(__file__), "public")
    if req.path == "/" or req.path == "/index.html":
        return serve_file(req, base, "index.html")
    if req.path.startswith("/static/"):
        sub = req.path[len("/static/"):]
        return serve_file(req, base, sub)
    return router.dispatch(req)


app = exception_middleware(_app)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the opensource_suncheon HTTP server.")
    host_default = os.environ.get(HOST_ENV, DEFAULT_HOST)
    port_default_text = os.environ.get(PORT_ENV, str(DEFAULT_PORT))
    try:
        port_default = int(port_default_text)
    except ValueError:
        parser.error(f"{PORT_ENV} must be an integer")

    parser.add_argument("--host", default=host_default, help=f"host interface to bind (env: {HOST_ENV})")
    parser.add_argument("--port", type=int, default=port_default, help=f"port to bind (env: {PORT_ENV})")
    return parser.parse_args()


def main() -> None:
    from shs.server import serve

    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(f"Serving on http://{args.host}:{args.port} ...")
    serve(args.host, args.port, app)


if __name__ == "__main__":
    main()
