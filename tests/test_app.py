from __future__ import annotations

import json
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from shs.request import Request


def request(method: str, path: str, query: dict[str, str] | None = None) -> Request:
    query = query or {}
    return Request(
        method=method,
        target=path,
        path=path,
        query=query,
        version="HTTP/1.1",
    )


class BasicRouteTests(unittest.TestCase):
    def test_health_returns_200(self) -> None:
        res = app.app(request("GET", "/health"))

        self.assertEqual(res.status, 200)
        self.assertEqual(res.body, b"")

    def test_hello_uses_path_parameter(self) -> None:
        res = app.app(request("GET", "/hello/charsyam"))

        self.assertEqual(res.status, 200)
        self.assertEqual(res.body.decode("utf-8"), "hello charsyam\n")

    def test_existing_add_route_still_works(self) -> None:
        res = app.app(request("GET", "/add/2/3"))

        self.assertEqual(res.status, 200)
        self.assertEqual(res.body.decode("utf-8"), "result = 5\n")


class StudentApiTests(unittest.TestCase):
    def test_charsyam_arithmetic_functions(self) -> None:
        cases = [
            ("add", 12),
            ("minus", 8),
            ("multiply", 20),
            ("divide", 5.0),
        ]

        for func_name, expected in cases:
            with self.subTest(func_name=func_name):
                res = app.app(request("GET", f"/api/v1/charsyam/{func_name}", {"a": "10", "b": "2"}))
                body = json.loads(res.body.decode("utf-8"))

                self.assertEqual(res.status, 200)
                self.assertEqual(body["user_id"], "charsyam")
                self.assertEqual(body["operation"], func_name)
                self.assertEqual(body["a"], 10)
                self.assertEqual(body["b"], 2)
                self.assertEqual(body["result"], expected)

    def test_missing_student_api_returns_404(self) -> None:
        res = app.app(request("GET", "/api/v1/missing/add", {"a": "10", "b": "2"}))

        self.assertEqual(res.status, 404)
        self.assertEqual(res.body.decode("utf-8"), "Student API not found")

    def test_missing_student_function_returns_404(self) -> None:
        res = app.app(request("GET", "/api/v1/charsyam/mod", {"a": "10", "b": "2"}))

        self.assertEqual(res.status, 404)
        self.assertEqual(res.body.decode("utf-8"), "Student API function not found")

    def test_divide_by_zero_returns_400(self) -> None:
        res = app.app(request("GET", "/api/v1/charsyam/divide", {"a": "10", "b": "0"}))

        self.assertEqual(res.status, 400)
        self.assertEqual(res.body.decode("utf-8"), "b must not be 0")

    def test_invalid_function_name_returns_400(self) -> None:
        res = app.app(request("GET", "/api/v1/charsyam/_private"))

        self.assertEqual(res.status, 400)
        self.assertEqual(res.body.decode("utf-8"), "Invalid function name")

    def test_student_function_exception_returns_json_500(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            student_dir = Path(tmp) / "broken"
            student_dir.mkdir()
            (student_dir / "func.py").write_text(
                "def fail(req, params):\n"
                "    raise ValueError('sample failure')\n",
                encoding="utf-8",
            )

            with patch.object(app, "STUDENT_API_ROOT", Path(tmp)), patch.object(app.logging, "exception"):
                res = app.app(request("GET", "/api/v1/broken/fail"))

        body = json.loads(res.body.decode("utf-8"))
        self.assertEqual(res.status, 500)
        self.assertEqual(body["error"]["type"], "ValueError")
        self.assertEqual(body["error"]["message"], "sample failure")

    def test_student_module_load_exception_returns_json_500(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            student_dir = Path(tmp) / "broken"
            student_dir.mkdir()
            (student_dir / "func.py").write_text("raise RuntimeError('load failure')\n", encoding="utf-8")

            with patch.object(app, "STUDENT_API_ROOT", Path(tmp)), patch.object(app.logging, "exception"):
                res = app.app(request("GET", "/api/v1/broken/add"))

        body = json.loads(res.body.decode("utf-8"))
        self.assertEqual(res.status, 500)
        self.assertEqual(body["error"]["type"], "RuntimeError")
        self.assertEqual(body["error"]["message"], "load failure")


class ServerOptionTests(unittest.TestCase):
    def test_default_host_and_port(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["app.py"]):
            args = app.parse_args()

        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 8081)

    def test_environment_host_and_port(self) -> None:
        env = {"SHS_HOST": "127.0.0.1", "SHS_PORT": "9000"}
        with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["app.py"]):
            args = app.parse_args()

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 9000)

    def test_cli_options_override_environment(self) -> None:
        env = {"SHS_HOST": "127.0.0.1", "SHS_PORT": "9000"}
        argv = ["app.py", "--host", "0.0.0.0", "--port", "8082"]
        with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", argv):
            args = app.parse_args()

        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 8082)

    def test_invalid_environment_port_exits_with_error(self) -> None:
        env = {"SHS_PORT": "not-a-port"}
        with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["app.py"]):
            with patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
                app.parse_args()


if __name__ == "__main__":
    unittest.main()
