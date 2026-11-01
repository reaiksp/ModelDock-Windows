# ModelDock

Companion chat: [ModelDock Chat (MDC)](https://github.com/reaiksp/ModelDock-Chat) — personas, memory, slang and local voice.

[简体中文](README.md) | **English**

ModelDock is a Windows desktop app for deploying local text models through the Ollama CLI. It detects the user's hardware, recommends a model, downloads it, verifies loading, and provides local API examples.

Development assistance: **OpenAI Codex**. The initial application code and documentation were developed with Codex assistance.

Repository: [ModelDock-Windows](https://github.com/reaiksp/ModelDock-Windows). For personalities, persistent conversations, memory and slang learning, use the independent companion [ModelDock Chat (MDC)](https://github.com/reaiksp/ModelDock-Chat). The two applications use separate repositories and data directories.

## In-app language switching and user input

Use **Language / 语言** in the sidebar to switch immediately between Simplified Chinese and English. The choice persists across restarts. AI reply language is a separate preference: follow the user's input, Simplified Chinese, or English. An explicit reply preference is included in the request; changing the interface language does not change that preference.

Typed input, personalities, provider/model names and memory records retain their original text. Internal configuration values remain stable across locales. MDC keeps unsent drafts per conversation and includes language-adaptation instructions in context budgeting. The application adapts a copy of the outgoing prompt; stored user messages are not rewritten.

![English desktop UI (demo configuration)](docs/images/desktop-en.png)

## Quick start

Supported target: Windows 10 22H2 or Windows 11, x64.

1. Extract the entire portable package and run `ModelDock.exe`. Keep the `_internal` directory next to it. Python is not required for the packaged application.
2. Choose general chat or coding, then choose balanced, speed or quality preference.
3. Click the recommendation/deployment button. If Ollama is missing, ModelDock downloads its official installer and checks the Windows signature before running it.
4. Deployment runs `ollama serve` and `ollama pull <model>`, then checks that the model can load.
5. Use the local chat page or copy an API example into your own application.

The initial runtime and model downloads require internet access and sufficient disk space. Ollama and model weights are not bundled. Cancelled model downloads can be retried; Ollama reuses downloaded parts.

## Recommendations

The catalog includes Qwen 3 general-purpose text models and Qwen 2.5 Coder models. Recommendations account for available system memory, confirmed free NVIDIA VRAM, and free space on the model drive.

System memory reserves at least 3 GiB or 20% of total RAM; VRAM reserves at least 1 GiB or 12%. RAM and VRAM are not simply added together. The first NVIDIA GPU is used to match MDC local speech on CUDA 0. CPU balanced/speed recommendations favor smaller models.

Base estimates assume default quantization at 4K; longer-context mode reserves additional space for 16K. Actual requirements vary with model versions, drivers, context and background applications. A recommendation is an estimate; successful loading is the final check. When independent VRAM cannot be confirmed, including some AMD/Intel configurations, the app uses a conservative system-memory estimate. Ollama decides which acceleration is available.

## Local APIs

Default server: `http://127.0.0.1:11434`.

- `GET /api/tags`: installed models.
- `POST /api/chat`: native Ollama chat.
- `POST /v1/chat/completions`: OpenAI-compatible chat.

```python
# pip install openai
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")
response = client.chat.completions.create(
    model="qwen3:1.7b",  # Replace with an installed model tag.
    messages=[{"role": "user", "content": "Hello!"}],
    reasoning_effort="none",
)
print(response.choices[0].message.content)
```

The API key above is a placeholder: local Ollama does not authenticate it. Servers started by ModelDock bind to loopback. If an existing Ollama server is reused, its existing network configuration applies. Closing ModelDock cancels its current task but leaves Ollama running for other API clients.

## Storage and troubleshooting

- Preferences and application logs: `%LOCALAPPDATA%\ModelDock`.
- Model files: Ollama's default `~/.ollama/models`, or the process/current-user `OLLAMA_MODELS` environment variable. An already-running Ollama instance uses its own environment; keep these settings consistent.
- In-window chat is held in memory. For persistent chat and memory, use MDC.
- Failed downloads: check network/proxy access and free space, then retry.
- Loading failures: free memory or select a smaller model.
- Unrecognized NVIDIA GPU: check that its driver and `nvidia-smi` work.
- Installer signature failure: install Ollama from its official site, then retry.

## Ollama CLI statement

ModelDock is an independent GUI project that uses the [official Ollama CLI](https://github.com/ollama/ollama) and HTTP APIs. It is not an official Ollama client and is not affiliated with Ollama. Ollama and individual model weights are governed by their respective licenses. See [Ollama for Windows](https://docs.ollama.com/windows), [chat API](https://docs.ollama.com/api/chat), and [Ollama's license](https://github.com/ollama/ollama/blob/main/LICENSE).

## Development and packaging

Use Python 3.12 on Windows x64:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The build produces a portable directory, ZIP and SHA256 file in `dist/`. Dynamic Qt/PySide6 libraries, license notices and application source are included. Keep those files together and preserve the ability to replace compatible LGPL libraries.

This is an unsigned early test build. Clean Windows installation, driver coverage and real download connectivity still require environment-specific acceptance testing. See [release notes](RELEASE_NOTES.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

## 两种容量模式 / Two capacity modes

“大体量”以 4K 上下文优先选择可容纳的较大 Q4 文字模型；“大上下文”使用 16K，额外预留 4 GiB 上下文预算，通常选择更轻的模型。该余量是保守估算，不是精确 KV cache 计算或速度承诺；实际以上下文元数据和成功加载为准。资源不足不会假称可用。超出目录上限或低配置时不保证两种模式一定选出不同标签。

开启本地 0.6B / 1.7B 语音时，分别预留 4 / 7 GiB 显存及 4 / 5 GiB 内存。云端语音不计本地模型预算。模型权重不因模式改变，模式配置影响推荐和上下文。

MD 成功部署后按模型保存方案。MDC“连接设置 → 应用 MD 部署方案”可显式导入模型、上下文与语音预算；不改写用户输入、人格或 API 密钥。MDC 按模型记住上下文，仍用模型元数据限制实际值。导入语音预算不代表语音模型已安装，需在语音页安装并启动服务。

[语音录音、克隆与训练支持核对](docs/SPEECH_CAPABILITIES.md)。

English: Larger-model mode prioritizes model size at 4K. Longer-context mode reserves an additional 4 GiB at 16K and typically recommends a smaller model. Both reserve local speech resources. These are planning estimates, not exact memory guarantees. MDC explicitly imports successful MD plans and clamps context to model metadata. Importing a speech budget does not install the speech model. User content and API credentials are preserved.
