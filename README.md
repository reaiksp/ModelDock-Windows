# ModelDock

配套聊天：[ModelDock Chat（MDC）](https://github.com/reaiksp/ModelDock-Chat) · 人格、记忆、黑话与语音。

**简体中文** | [English](README.en.md)

面向 Windows 10 22H2 / Windows 11 x64 的本地文字模型桌面软件。界面使用 PySide6，推理由 Ollama 命令行运行环境提供。版本：0.4.0。

开发协作署名：**OpenAI Codex**（AI 编程助手）。本项目初版代码与文档由 Codex 协助完成。

## 压缩大模型实验（0.4.0）

新增用途 **“压缩大模型”**，提供 [ISTA-DASLab 发布的 Qwen3.8-27B GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF)。四个选项属于**同一 27B 参数家族的不同位宽**，不是改用 0.5B 或 1B 小模型。目录指定完整文件名；本更新只部署经过固定版本与 SHA-256 校验的文字 GGUF，经 Ollama CLI 导入，不提供视觉输入，也不下载视觉投影或 MTP 附加文件。官方文件大小与运行内存分别列出。已有用途和用户保存的选择保留。

| 量化档位 | 下载预算（GiB） | 4K 运行预算（GiB） |
| --- | ---: | ---: |
| IQ2_XS | 8.0 | 10.0 |
| IQ2_S | 8.8 | 10.8 |
| IQ3_XXS | 9.5 | 11.5 |
| IQ3_S | 11.1 | 13.0 |

这些数字是选型用的保守估算，**文件大小不等于显存需求**。推荐仍预留系统、下载、16K 上下文和本地语音资源；内存和显存不相加。配置不足时明确不给出该方案，不会悄悄换成小参数模型。CPU 用户可以主动选择“质量优先”，但 27B 生成可能很慢，加载成功也不代表交互速度合适。

“速度优先”在可容纳的同家族档位中选择较低资源的一档；“质量优先”倾向较高位宽。GSQ + RCO 与低位宽量化不意味着质量无损，重复提示也不能消除量化误差或突破上下文。较旧 Ollama 版本未必识别该架构或量化格式，必须以实际下载、加载与生成检查为准。

成功部署后，MDC 可在“连接设置 → 应用 MD 部署方案”导入模型、4K / 16K 上下文和语音预算。它不会重写人格、用户输入、资料或 API 密钥。

## 应用内中英文与输入适配

侧栏 **Language / 语言** 可即时切换简体中文与 English，重启后保留。界面语言与 AI 回复语言独立：聊天页或连接设置中可选“跟随用户输入 / 简体中文 / English”。明确语言偏好会加入请求提示；界面切换不会改写用户的输入文字、人格提示词、供应商 / 模型名或记忆原文。

推荐用途、速度 / 质量偏好与 API 配置使用稳定内部值，不因翻译改变。请求的语言适配开销会参与 MDC 的上下文预算。MDC 还会按会话保存未发送草稿，切换和重启后可恢复。

## 给普通用户

下载 `ModelDock-0.4.0-windows-x64.zip`，**完整解压**后双击 `ModelDock.exe`。无需安装 Python，也无需云端 API 密钥。不要只复制 exe，旁边的 `_internal` 目录是必要依赖。

1. 打开软件，自动检测处理器、系统内存、可用内存、NVIDIA 空闲显存与模型存储盘空间。
2. 选择“通用对话 / 代码开发”和“均衡 / 速度优先 / 质量优先”。
3. 点击“一键推荐并部署”。若缺少 Ollama，从官网下载并验证 Windows 数字签名后安装；随后调用真实的 `ollama serve`、`ollama pull <模型>`，下载完成后加载并检查模型。
4. 在“本地对话”使用模型，或在“API 接入”复制 Python、PowerShell、cURL 示例。

首次下载需要联网，模型下载可能较大。已有 Ollama 和模型时会复用。取消下载后可重试，Ollama 会复用已下载的分片。安装软件与下载模型都会占用磁盘空间。

## Ollama CLI 声明

ModelDock 是独立的图形化桌面项目，通过调用 [Ollama 官方命令行工具（CLI）](https://github.com/ollama/ollama)的 `ollama serve`、`ollama pull` 命令启动本地服务、下载模型，并使用其 HTTP API 完成推理。模型运行能力由 Ollama 提供。

本项目不是 Ollama 官方客户端，与 Ollama 项目无隶属关系。发行包不内置 Ollama 安装程序或模型权重；Ollama 及模型分别从官方来源下载，并遵循各自的许可证。使用与配置方法请参阅 [Ollama Windows 官方文档](https://docs.ollama.com/windows)，上游许可请参阅 [Ollama LICENSE](https://github.com/ollama/ollama/blob/main/LICENSE)。

## 功能与推荐依据

- 精选 Qwen 3 通用文字模型（0.6B—32B）与 Qwen 2.5 Coder（0.5B—32B），常规标签从 Ollama 仓库下载；压缩大模型使用明确的上游 GGUF 文件。
- 系统内存保留至少 3 GiB 或总量的 20%，同时受当前可用内存限制；显存保留至少 1 GiB 或 12%。不把独显显存与内存直接相加，使用 NVIDIA 首卡空闲显存，与 MDC 本地语音的 CUDA 0 一致。
- CPU 方案在“均衡 / 速度优先”下限制推荐规模。“质量优先”可以推荐更大的内存模型，生成速度会更慢。
- 磁盘预留下载体积的 15% 和额外 1 GiB；部署前再次检查模型盘空间。
- 基础内存按默认量化和 4K 估算，大上下文模式另预留 16K 所需余量。模型实际体积、KV 缓存、驱动占用及速度会有差异，推荐是启发式估算，加载验证才是最终结果。
- NVIDIA 使用 `nvidia-smi` 的实际空闲显存。AMD、Intel 或无法确认独立显存的设备使用保守内存方案；Ollama 仍可根据自身驱动支持启用硬件加速。
- 运行环境安装、模型下载、加载验证和对话在后台执行，界面显示真实状态。网络错误、磁盘不足及加载失败会显示原因。
- 对话支持流式输出、停止生成、切换模型和清空历史。窗口内最多发送最近 20 条消息，推理上下文按成功部署方案配置为 4096 或 16384；更早的内容可能被截断。

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

## 两种容量模式 / Two capacity modes

“大体量”以 4K 上下文优先选择可容纳的较大文字模型或同家族较高位宽版本；“大上下文”使用 16K，额外预留 4 GiB 上下文预算，通常选择更轻的模型。该余量是保守估算，不是精确 KV cache 计算或速度承诺；实际以上下文元数据和成功加载为准。资源不足不会假称可用。超出目录上限或低配置时不保证两种模式一定选出不同标签。

开启本地 0.6B / 1.7B 语音时，分别预留 4 / 7 GiB 显存及 4 / 5 GiB 内存。云端语音不计本地模型预算。模型权重不因模式改变，模式配置影响推荐和上下文。

MD 成功部署后按模型保存方案。MDC“连接设置 → 应用 MD 部署方案”可显式导入模型、上下文与语音预算；不改写用户输入、人格或 API 密钥。MDC 按模型记住上下文，仍用模型元数据限制实际值。导入语音预算不代表语音模型已安装，需在语音页安装并启动服务。

[语音录音、克隆与训练支持核对](docs/SPEECH_CAPABILITIES.md)。

English: Larger-model mode prioritizes model size at 4K. Longer-context mode reserves an additional 4 GiB at 16K and typically recommends a smaller model. Both reserve local speech resources. These are planning estimates, not exact memory guarantees. MDC explicitly imports successful MD plans and clamps context to model metadata. Importing a speech budget does not install the speech model. User content and API credentials are preserved.
