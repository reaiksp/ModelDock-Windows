# ModelDock

面向 Windows 10 22H2 / Windows 11 x64 的本地文字模型桌面软件。界面使用 PySide6，推理由 Ollama 命令行运行环境提供。版本：0.1.0。

## 给普通用户

下载 `ModelDock-0.1.0-windows-x64.zip`，**完整解压**后双击 `ModelDock.exe`。无需安装 Python，也无需云端 API 密钥。不要只复制 exe，旁边的 `_internal` 目录是必要依赖。

1. 打开软件，自动检测处理器、系统内存、可用内存、NVIDIA 空闲显存与模型存储盘空间。
2. 选择“通用对话 / 代码开发”和“均衡 / 速度优先 / 质量优先”。
3. 点击“一键推荐并部署”。若缺少 Ollama，从官网下载并验证 Windows 数字签名后安装；随后调用真实的 `ollama serve`、`ollama pull <模型>`，下载完成后加载并检查模型。
4. 在“本地对话”使用模型，或在“API 接入”复制 Python、PowerShell、cURL 示例。

首次下载需要联网，模型下载可能较大。已有 Ollama 和模型时会复用。取消下载后可重试，Ollama 会复用已下载的分片。安装软件与下载模型都会占用磁盘空间。

## 功能与推荐依据

- 精选 Qwen 3 通用文字模型（0.6B—32B）与 Qwen 2.5 Coder（0.5B—32B），均从 Ollama 官方仓库下载。
- 系统内存保留至少 3 GiB 或总量的 20%，同时受当前可用内存限制；显存保留至少 1 GiB 或 12%。不把独显显存与内存直接相加，多卡取单卡最大空闲显存。
- CPU 方案在“均衡 / 速度优先”下限制推荐规模。“质量优先”可以推荐更大的内存模型，生成速度会更慢。
- 磁盘预留下载体积的 15% 和额外 1 GiB；部署前再次检查模型盘空间。
- 内存估算按默认量化、4K 上下文计算。模型实际体积、KV 缓存、驱动占用及速度会有差异，推荐是启发式估算，加载验证才是最终结果。
- NVIDIA 使用 `nvidia-smi` 的实际空闲显存。AMD、Intel 或无法确认独立显存的设备使用保守内存方案；Ollama 仍可根据自身驱动支持启用硬件加速。
- 运行环境安装、模型下载、加载验证和对话在后台执行，界面显示真实状态。网络错误、磁盘不足及加载失败会显示原因。
- 对话支持流式输出、停止生成、切换模型和清空历史。窗口内最多发送最近 20 条消息，推理上下文配置为 4096；更早的内容可能被截断。

## API

服务地址：`http://127.0.0.1:11434`。

- `GET /api/tags`：已安装模型。
- `POST /api/chat`：Ollama 原生聊天接口。
- `POST /v1/chat/completions`：OpenAI 兼容聊天接口。
- OpenAI SDK 的 `base_url` 为 `http://127.0.0.1:11434/v1`，`api_key="ollama"` 只是占位值，本地 Ollama 不校验密钥。

```python
# pip install openai
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")
response = client.chat.completions.create(
    model="qwen3:1.7b",  # 改为已安装的模型标签
    messages=[{"role": "user", "content": "你好"}],
    reasoning_effort="none",
)
print(response.choices[0].message.content)
```

本软件启动的 Ollama 绑定本机回环地址。复用已有服务时，监听范围取决于已有 Ollama 配置。当前版本没有远程 API 网关、用户鉴权或公网发布功能。关闭桌面窗口会取消当前任务，Ollama 服务保留运行，供其他本机程序继续调用。

## 存储与排错

- 默认模型目录为 `~/.ollama/models`，尊重进程或 Windows 当前用户的 `OLLAMA_MODELS` 环境变量。复用已有服务时，其实际存储目录由该服务决定；若使用系统级或自定义启动环境，请保证与当前用户的 `OLLAMA_MODELS` 一致。
- 偏好设置：`%LOCALAPPDATA%\ModelDock\settings.json`。
- 桌面日志：`%LOCALAPPDATA%\ModelDock\modeldock.log`，自动轮转。
- 本软件启动的服务日志：`%LOCALAPPDATA%\ModelDock\ollama-server.log`。
- 对话内容仅保留在窗口内存中，桌面日志不记录聊天正文。
- 下载失败：检查网络、代理和模型盘空间，点击部署重试。
- 加载失败 / 内存不足：关闭其他程序，重新检测或选择更小模型。
- 未识别 NVIDIA：安装可用驱动，确认 `nvidia-smi` 正常运行。
- 数字签名校验失败：软件不会执行安装包，请从 https://ollama.com/download 手动安装后重试。
- 企业代理、杀毒软件、首次运行 SmartScreen 提示以及 Ollama 官方安装程序的交互行为可能因电脑环境不同而不同。

## 开发

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m pytest -q
```

真实下载 / 推理联调（会下载约 0.5 GiB 的 `qwen3:0.6b`，保存在 Ollama 模型目录）：

```powershell
.\.venv\Scripts\python.exe tools\integration_smoke.py
```

## 打包与分发

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

生成 `dist/ModelDock/ModelDock.exe`、完整便携 ZIP 和 SHA256 校验文件。构建脚本默认使用 `.venv`，可通过 `-Python <python路径>` 选择构建环境。在 Windows x64、Python 3.12 上构建。

便携包不内置 Ollama 或模型权重，首次部署从官方源安装 / 下载；因此首次使用不是离线安装。发布版本应在无 Python、无 Ollama 的干净 Windows 机器上做验收，并按发行主体签署 exe；当前构建为未签名的早期测试版。

动态 Qt / PySide6 DLL 保留在 `_internal`，随发行包附带第三方许可证与来源说明。分发时保留这些文件，并允许接收者按 LGPL 条款替换相关动态库。模型许可证由对应模型发布方提供，下载与使用前可在官方模型页面查看。详细说明见 `THIRD_PARTY_NOTICES.md`。

## 官方资料

- Ollama Windows：https://docs.ollama.com/windows
- Ollama 聊天 API：https://docs.ollama.com/api/chat
- OpenAI 兼容接口：https://docs.ollama.com/api/openai-compatibility
- Qwen 3 模型：https://ollama.com/library/qwen3
- Qwen Coder 模型：https://ollama.com/library/qwen2.5-coder

## 源码结构

`main.py` 为入口；`modeldock/ui.py` 为桌面界面与任务调度；`system.py` 为硬件与路径检测；`catalog.py` 为模型目录与推荐规则；`runtime.py` 为 CLI / HTTP 集成；`tests/` 为推荐与协议测试；`tools/` 为预览、真实联调和打包辅助脚本。
