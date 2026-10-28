"""Ollama CLI lifecycle and loopback-only HTTP client. No shell interpolation."""
import codecs
import http.client
import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from .i18n import response_policy, adapt_user_message
from .system import DATA_DIR, FLAGS, command, find_ollama, model_dir

HOST, PORT = "127.0.0.1", 11434
BASE_URL = f"http://{HOST}:{PORT}"


class Cancelled(Exception):
    pass


class Task:
    def __init__(self):
        self.event = threading.Event()
        self.process = None
        self.connection = None

    def check(self):
        if self.event.is_set():
            raise Cancelled("操作已取消；已下载的分片可在下次继续。")

    def cancel(self):
        self.event.set()
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except OSError:
                pass
        conn = self.connection
        if conn and conn.sock:
            try:
                conn.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def request(path, body=None, timeout=5, task=None):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    if task:
        task.check()
        task.connection = conn
    try:
        conn.request("GET" if body is None else "POST", path,
                     body=None if body is None else json.dumps(body).encode(),
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        payload = response.read()
        if response.status >= 400:
            raise RuntimeError(f"Ollama HTTP {response.status}：{payload.decode('utf-8', 'replace')[:500]}")
        return json.loads(payload)
    except (OSError, ValueError, http.client.HTTPException) as exc:
        if task:
            task.check()
        raise RuntimeError(f"本地服务请求失败：{exc}") from exc
    finally:
        conn.close()
        if task:
            task.connection = None


def status():
    try:
        return request("/api/version", timeout=2).get("version", "未知")
    except RuntimeError:
        return None


def installed():
    return request("/api/tags").get("models", [])


def cli_env():
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"{HOST}:{PORT}"
    env["OLLAMA_MODELS"] = str(model_dir())
    env["NO_COLOR"] = "1"
    return env


def ensure_server(task, log):
    task.check()
    if status():
        log("已连接本机 Ollama 服务。")
        return
    cli = find_ollama()
    if not cli:
        raise RuntimeError("尚未安装 Ollama。请先点击“安装运行环境”，完成安装后重新部署。")
    log("执行：ollama serve（127.0.0.1:11434）")
    # The service intentionally survives the GUI so external API clients keep working.
    with (DATA_DIR / "ollama-server.log").open("ab") as output:
        proc = subprocess.Popen([cli, "serve"], env=cli_env(), stdout=output, stderr=output,
                                stdin=subprocess.DEVNULL, creationflags=FLAGS)
    for _ in range(80):
        task.check()
        if status():
            return
        if proc.poll() is not None:
            # Another concurrent server may have won the bind.
            if status():
                return
            raise RuntimeError(f"Ollama 启动失败，请检查 {DATA_DIR / 'ollama-server.log'}")
        task.event.wait(.25)
    raise RuntimeError("Ollama 启动超时，请查看诊断日志并重试。")


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def pull(tag, task, log, progress):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,160}", tag):
        raise ValueError("模型名称格式无效。")
    ensure_server(task, log)
    cli = find_ollama()
    if not cli:
        raise RuntimeError("Ollama CLI 不可用，请安装运行环境。")
    log(f"执行：ollama pull {tag}")
    proc = subprocess.Popen([cli, "pull", tag], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, env=cli_env(), creationflags=FLAGS)
    task.process = proc
    if task.event.is_set():
        task.cancel()
    tail, last_text, last_line, last_time = "", "", "", 0.0
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    try:
        while True:
            task.check()
            chunk = os.read(proc.stdout.fileno(), 2048)
            if not chunk:
                break
            # Windows Ollama redraws using CSI 1G instead of CR, even on pipes.
            # Treat cursor-to-column-one as a line boundary before stripping ANSI.
            tail += decoder.decode(chunk)
            tail = re.sub(r"\x1b\[(?:1)?G", "\r", tail)
            parts = re.split(r"[\r\n]", tail)
            tail = parts.pop()[-16384:]
            for line in parts:
                line = ANSI.sub("", line).strip()
                if not line:
                    continue
                last_line = line
                match = re.search(r"(\d{1,3})%", line)
                if match:
                    progress(min(99, int(match.group(1))), line)
                now = time.monotonic()
                if line != last_text and (now - last_time > 1.5 or any(word in line.lower() for word in ["success", "error"])):
                    log(line)
                    last_text, last_time = line, now
        task.check()
        code = proc.wait(timeout=10)
        if code:
            detail = ANSI.sub("", tail).strip() or last_line
            raise RuntimeError(f"模型下载失败（退出码 {code}）。{detail[-1000:]}\n请检查网络及磁盘后重试。")
        if tag not in {m.get("name") for m in installed()}:
            raise RuntimeError("下载命令结束，但本地模型列表中未找到目标模型。请刷新后重试。")
        progress(100, "模型已下载并校验，正在准备推理…")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        proc.stdout.close()
        task.process = None


def warmup(tag, task, log):
    log("加载模型并验证推理接口…")
    result = request("/api/generate", {"model": tag, "prompt": "", "stream": False,
                     "keep_alive": "5m", "options": {"num_ctx": 4096}}, timeout=180, task=task)
    if not result.get("done"):
        raise RuntimeError("模型加载未完成，请在本地对话中重试。")
    log("部署完成，模型可通过本地 API 调用。")
    return tag


def deploy(tag, task, log, progress):
    pull(tag, task, log, progress)
    return warmup(tag, task, log)


def stream_chat(tag, messages, task, emit, response_language="auto"):
    task.check()
    messages = [dict(m) for m in messages]
    for message in reversed(messages):
        if message.get('role') == 'user':
            message['content'] = adapt_user_message(message['content'], response_language)
            break
    conn = http.client.HTTPConnection(HOST, PORT, timeout=180)
    task.connection = conn
    try:
        conn.request("POST", "/api/chat", json.dumps({"model": tag, "messages": [{"role":"system","content":response_policy(response_language)}] + messages,
                     "stream": True, "think": False, "options": {"num_ctx": 4096}}).encode(),
                     {"Content-Type": "application/json"})
        response = conn.getresponse()
        if response.status >= 400:
            raise RuntimeError(response.read().decode("utf-8", "replace")[:600])
        answer, done = "", False
        while True:
            task.check()
            line = response.readline()
            if not line:
                break
            data = json.loads(line)
            if data.get("error"):
                raise RuntimeError(data["error"])
            token = data.get("message", {}).get("content", "")
            answer += token
            if token:
                emit(token)
            if data.get("done"):
                done = True
                break
        task.check()
        if not done:
            raise RuntimeError("生成连接提前结束，请重试。")
        return answer
    except (OSError, ValueError, http.client.HTTPException) as exc:
        task.check()
        raise RuntimeError(f"生成失败：{exc}") from exc
    finally:
        conn.close()
        task.connection = None


def install_runtime(task, log, progress):
    if os.name != "nt":
        raise RuntimeError("当前自动安装功能支持 Windows，请从 ollama.com 手动安装。")
    if find_ollama():
        log("Ollama 已安装。")
        return find_ollama()
    installer = DATA_DIR / "OllamaSetup.exe"
    partial = installer.with_suffix(".part")
    log("从 Ollama 官方站点下载 Windows 安装程序…")
    try:
        with urllib.request.urlopen("https://ollama.com/download/OllamaSetup.exe", timeout=30) as response:
            total = int(response.headers.get("Content-Length", 0))
            count = 0
            with partial.open("wb") as file:
                while chunk := response.read(1024 * 256):
                    task.check()
                    file.write(chunk)
                    count += len(chunk)
                    progress(int(count / total * 95) if total else -1,
                             f"运行环境已下载 {count / 1024**2:.1f} MiB")
        task.check()
        partial.replace(installer)
        log("校验安装程序的 Windows 数字签名…")
        # Path is supplied through an environment variable, never interpolated as code.
        env = os.environ.copy()
        env["MODELDOCK_INSTALLER"] = str(installer)
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
            "$s=Get-AuthenticodeSignature -LiteralPath $env:MODELDOCK_INSTALLER; "
            "if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Ollama'){exit 1}"],
            env=env, creationflags=FLAGS, timeout=60, capture_output=True)
        if result.returncode:
            raise RuntimeError("安装程序数字签名校验未通过，请从 https://ollama.com/download 手动安装。")
        task.check()
        log("正在安装 Ollama，首次安装可能需要几分钟…")
        proc = subprocess.Popen([str(installer), "/VERYSILENT", "/NORESTART"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, creationflags=FLAGS)
        task.process = proc
        while proc.poll() is None:
            task.check()
            task.event.wait(.5)
        task.check()
        if proc.returncode or not find_ollama():
            raise RuntimeError("运行环境安装未完成，请使用官网安装程序后重试。")
        progress(100, "Ollama 安装完成")
        return find_ollama()
    finally:
        task.process = None
        partial.unlink(missing_ok=True)


def one_click(tag, task, log, progress):
    if not find_ollama():
        install_runtime(task, log, progress)
    return deploy(tag, task, log, progress)
