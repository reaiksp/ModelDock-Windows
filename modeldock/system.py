import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil

FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
DATA_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "ModelDock"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def command(args, timeout=20):
    result = subprocess.run(args, capture_output=True, timeout=timeout,
                            creationflags=FLAGS, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"命令失败：{args[0]}")
    return result.stdout.strip().lstrip("\ufeff")


def user_env(name):
    if os.getenv(name):
        return os.getenv(name)
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                return str(winreg.QueryValueEx(key, name)[0])
        except OSError:
            pass
    return None


def model_dir():
    return Path(os.path.expandvars(user_env("OLLAMA_MODELS") or str(Path.home() / ".ollama/models")))


def disk_free(path):
    path = Path(path).resolve()
    while not path.exists() and path.parent != path:
        path = path.parent
    return shutil.disk_usage(path).free / 1024**3


def find_ollama():
    for path in [shutil.which("ollama"),
                 str(Path(os.getenv("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe"),
                 str(Path(os.getenv("ProgramFiles", "C:/Program Files")) / "Ollama/ollama.exe")]:
        if path and Path(path).is_file():
            return path
    return None


@dataclass
class Hardware:
    cpu: str
    cores: int
    ram: float
    available: float
    gpu: str
    vram: float
    disk: float
    models_path: str
    note: str = ""


def detect():
    mem = psutil.virtual_memory()
    cpu = platform.processor() or "未知处理器"
    gpu, vram = "未检测到可确认的独立显存", 0.0
    notes = []
    smi = shutil.which("nvidia-smi")
    if not smi:
        candidate = Path(os.getenv("SystemRoot", "C:/Windows")) / "System32/nvidia-smi.exe"
        smi = str(candidate) if candidate.exists() else None
    if smi:
        try:
            rows = command([smi, "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"])
            cards = []
            for row in rows.splitlines():
                name, total, free = [v.strip() for v in row.rsplit(",", 2)]
                cards.append((float(free) / 1024, name, float(total) / 1024))
            vram, name, total = max(cards)
            gpu = f"{name} · {total:.0f} GiB"
            notes.append("独立显存按空闲值计算，多显卡取单卡最大值。")
        except (ValueError, RuntimeError, subprocess.TimeoutExpired):
            notes.append("NVIDIA 显存读取失败，使用保守的内存推荐。")
    if os.name == "nt":
        try:
            data = json.loads(command(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                "@{cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name);"
                "gpu=@(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name)} | ConvertTo-Json -Compress"]))
            cpu = data.get("cpu") or cpu
            if not vram:
                gpu = " / ".join(data.get("gpu") or []) or gpu
                notes.append("集成显卡或未知显存不叠加到内存；AMD / Intel 加速由 Ollama 实际检测。")
        except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired):
            notes.append("部分硬件信息无法读取。")
    path = model_dir()
    return Hardware(cpu, psutil.cpu_count(logical=True) or 1, mem.total / 1024**3,
                    mem.available / 1024**3, gpu, vram, disk_free(path), str(path), " ".join(notes))


def load_settings():
    try:
        result = json.loads((DATA_DIR / "settings.json").read_text("utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data):
    target = DATA_DIR / "settings.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    temp.replace(target)
