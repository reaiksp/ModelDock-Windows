"""Explicit real integration check; downloads a 0.5 GiB model if absent."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modeldock import runtime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
task = runtime.Task()
last = [0]
def progress(value, text):
    if time.monotonic() - last[0] > 5:
        print(f"progress={value} {text}", flush=True)
        last[0] = time.monotonic()

tag = "qwen3:0.6b"
runtime.deploy(tag, task, lambda line: print(line, flush=True), progress)
tokens = []
answer = runtime.stream_chat(tag, [{"role": "user", "content": "Reply with the word hello."}], task, tokens.append)
assert answer.strip(), "Native chat returned no content"
result = runtime.request("/v1/chat/completions", {"model": tag,
    "messages": [{"role": "user", "content": "Say hello. /no_think"}],
    "stream": False, "max_tokens": 128}, timeout=120, task=task)
assert result.get("choices"), "OpenAI-compatible API returned no choices"
report = {"model": tag, "native_chat": answer,
          "openai_compatible": result, "status": "passed"}
path = Path(__file__).resolve().parents[1] / "artifacts" / "integration-result.json"
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
print("Integration smoke PASSED", flush=True)
