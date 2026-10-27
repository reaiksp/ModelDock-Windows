import json
import threading
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from modeldock import runtime


@pytest.fixture
def server(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"version":"test","models":[]}')

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(500 if body.get("model") == "bad" else 200)
            self.end_headers()
            if body.get("model") == "bad":
                self.wfile.write(b'{"error":"model unavailable"}')
            elif body.get("stream"):
                self.wfile.write(b'{"message":{"content":"hello"},"done":false}\n')
                if body.get("model") != "truncated":
                    self.wfile.write(b'{"message":{"content":" world"},"done":true}\n')
            else:
                self.wfile.write(b'{"done":true}')
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    monkeypatch.setattr(runtime, "PORT", httpd.server_port)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield
    httpd.shutdown()
    httpd.server_close()


def test_request_and_status(server):
    assert runtime.status() == "test"
    assert runtime.request("/api/generate", {"model": "ok"})["done"]


def test_stream_assembles_tokens(server):
    tokens = []
    result = runtime.stream_chat("ok", [], runtime.Task(), tokens.append)
    assert result == "hello world"
    assert tokens == ["hello", " world"]


def test_partial_stream_is_not_success(server):
    with pytest.raises(RuntimeError, match="提前结束"):
        runtime.stream_chat("truncated", [], runtime.Task(), lambda t: None)


def test_http_error_is_visible(server):
    with pytest.raises(RuntimeError, match="model unavailable"):
        runtime.request("/api/chat", {"model": "bad"})


def test_cancel_before_network(server):
    task = runtime.Task()
    task.cancel()
    with pytest.raises(runtime.Cancelled):
        runtime.stream_chat("ok", [], task, lambda t: None)


def test_model_tag_cannot_be_a_shell_command():
    with pytest.raises(ValueError):
        runtime.pull("qwen3; calc.exe", runtime.Task(), lambda t: None, lambda p, t: None)


def test_cli_windows_redraw_progress_is_parsed(monkeypatch):
    original = subprocess.Popen
    script = "import sys; sys.stdout.buffer.write(b'\\x1b[1Gpulling abc 42%\\x1b[1Gsuccess\\n'); sys.stdout.flush()"
    def spawn(args, **kwargs):
        assert args[1:] == ["pull", "qwen3:0.6b"]
        return original([sys.executable, "-u", "-c", script], **kwargs)
    monkeypatch.setattr(runtime, "ensure_server", lambda *a: None)
    monkeypatch.setattr(runtime, "find_ollama", lambda: "ollama.exe")
    monkeypatch.setattr(runtime, "installed", lambda: [{"name": "qwen3:0.6b"}])
    monkeypatch.setattr(runtime.subprocess, "Popen", spawn)
    progress, logs = [], []
    runtime.pull("qwen3:0.6b", runtime.Task(), logs.append, lambda v, t: progress.append(v))
    assert 42 in progress
    assert progress[-1] == 100
    assert any("success" in line for line in logs)


def test_cancel_terminates_cli_child(monkeypatch):
    original = subprocess.Popen
    children = []
    def spawn(args, **kwargs):
        child = original([sys.executable, "-u", "-c", "import time; print('waiting',flush=True); time.sleep(30)"], **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(runtime, "ensure_server", lambda *a: None)
    monkeypatch.setattr(runtime, "find_ollama", lambda: "ollama.exe")
    monkeypatch.setattr(runtime.subprocess, "Popen", spawn)
    task = runtime.Task()
    cancel = threading.Timer(.3, task.cancel)
    cancel.start()
    with pytest.raises(runtime.Cancelled):
        runtime.pull("qwen3:0.6b", task, lambda t: None, lambda v, t: None)
    cancel.join()
    assert children[0].poll() is not None
