# 0.5.2 · 2K一档上下文 / Context in2K increments

- 上下文五档统一为2K /4K /6K /8K /10K，默认保持4K。
- 旧偏好迁移后标记新刻度；已部署方案及当前聊天上下文不因拖动或升级而改变。
- 配套新版MD/MDC可精确导入2K/6K/10K，旧16K/32K方案仍保留实际上下文；记忆、黑话、API和用户原文保留。
- 上下文内存预留插值估算，语音独立资源门槛保持。2K不保证语音可运行。

English: Both applications now offer five context positions in2K increments, from2K through10K. Existing active/deployed contexts remain unchanged. New plans import exactly; old16K/32K plans remain usable. Speech resource requirements and original user data are preserved.

[说明 / Details](docs/DUAL_SLIDERS.md) · [MD](https://github.com/reaiksp/ModelDock-Windows) · [MDC](https://github.com/reaiksp/ModelDock-Chat)

验证：MD200项、MDC365项回归通过；8,640组双端联合推荐一致，原生界面与方案导入检查通过。 / Validation:200 MD and365 MDC tests,8,640 cross-application recommendation cases and native UI/import checks passed.

---

# 0.5.1 · 模型参数范围 / Parameter range

- 新增0.5B–48B参数上限滑条，0.5B步进，共96个位置；显示实际匹配模型，中间位置均参与推荐。
- 精度条下载对应参数家族的量化版本，保留对话、语音和磁盘联合预算；拖动不下载、不切换当前模型，保留主动下载按钮。
- 53个新增固定版本GGUF文件，包含0.5/0.6/1.5/1.7/3/4/7/8/14/32/46.7B档，另保留27B。48B上限当前匹配46.7B Mixtral MoE总参数；不是原生48B。32/46.7B缺少已接入单文件完全体时明确降精度。
- 用户原文、提示词、记忆、黑话和API设置保留；MD方案包含目标和实际参数，MDC可导入。
- 新增来源核对及范围回归测试；新增模型未全量下载推理，部署时仍要求实际加载成功。原精度和量化均不承诺记忆准确率。

English: A0.5B–48B parameter cap in0.5B steps selects a real family at or below the cap, then its feasible quantization. Actual parameters and fallback are visible. Dragging never downloads or switches the active model. Newly added files have pinned metadata, size and SHA256 verification; full inference was not performed for them.

[参数范围与完整来源 / Details and sources](docs/PARAMETER_RANGE.md) · [MD](https://github.com/reaiksp/ModelDock-Windows) · [MDC](https://github.com/reaiksp/ModelDock-Chat)

验证：MD193项、MDC354项回归测试通过；参数范围8,640组双端推荐一致。原生界面覆盖96个参数位置，打包程序启动与中英文检查通过。新增模型未全量推理。 / Validation:193 MD and354 MDC tests,8,640 cross-application recommendations, native96-position slider checks and frozen startup passed. New model weights were not fully tested for inference.

---

# ModelDock 0.5.0 · 双需求推荐条

配套聊天：[MDC](https://github.com/reaiksp/ModelDock-Chat) · 部署工具：[MD](https://github.com/reaiksp/ModelDock-Windows)

- 上方精度五档为同一 Qwen3.8-27B 的 IQ2_XS、IQ3_XXS、Q4_K_M、Q8_0 与真正 BF16 文字权重；旧 IQ2_S / IQ3_S 保留手动部署。
- 下方对话与记忆需求五档为 4K / 4K / 8K / 16K / 32K，与本地语音、系统、显存及磁盘联合推荐。资源不足时明确显示推荐降档，不静默缩短对话需求，也不改用小参数模型。
- 拖动仅推荐并保存偏好；保留用户主动点击下载按钮，不自动下载或切换当前模型。
- 成功部署后保存目标档、实际档、对话需求、上下文及语音预算，供 MDC 显式导入。原始输入、人格、API 配置与旧方案额外字段保留。
- 中英文界面与文档同步更新。详见[双需求与兼容策略](docs/DUAL_SLIDERS.md)。

## 本次验证 / Validation

- 88 项自动测试通过，原生进程正常退出；独立事件循环界面检查通过，覆盖拖动不下载、旧设置迁移、目标与实际档分离、语言切换保留原文、繁忙期间禁用滑条及模拟部署方案保存。
- 打包后的独立程序启动与双滑条范围、主动下载入口检查通过；中英文切换后的布局、推荐对比和说明文字检查通过。
- MD / MDC 共 2,025 组联合推荐结果一致，包含不同硬件、精度、对话需求及语音组合。
- Q4 / Q8 / BF16 的上游固定版本、精确文件、大小、SHA-256 与 GGUF 文件头已核对，尚未全量下载或推理。
- IQ2_XS 此前已通过真实 4K 加载、人格和记忆召回。本次 MDC 验证已确认记忆与黑话可共同保存到临时私有模型配置，候选排除、基础权重不变、测试快照已清理；当前内存／显存不足导致新生成召回试验未完成，不能据此宣称黑话学习质量或所有量化档的记忆准确率。
- 记忆写入是默认系统提示持久化，不是训练模型权重，仍占上下文；语音并发、32K、不同显卡与纯 CPU 性能需要对应硬件验收。

English: Two five-step requirement sliders combine same-27B precision, conversation/memory demand and local speech resources. Downloads remain user-initiated. 88 automated tests and a normal-exit native event-loop UI smoke passed. Q4/Q8/BF16 received pinned-source and metadata checks, not full inference. IQ2_XS approved-memory/slang configuration persistence passed in MDC; new generation/recall could not complete because available memory/VRAM was insufficient. Prompt persistence does not train model weights or guarantee memory accuracy.

---

# ModelDock 0.4.0 · 同参数大模型压缩实验

- 新增“压缩大模型”用途：同一 Qwen3.8-27B GSQ-RCO 家族的 IQ2_XS / IQ2_S / IQ3_XXS / IQ3_S 精确 GGUF 文件，不以小参数模型替代。
- 延续 4K 大体量 / 16K 大上下文和本地语音联合预算，手动部署与自动推荐共享资源校验。
- 模型卡提供来源说明；保留既有用途、用户选择和 MDC 部署方案导入兼容性。
- 内存不足时不给出该压缩方案；CPU 质量优先可主动尝试，界面提示速度可能很慢。
- 下载体积、运行估算和实际性能分开说明；不宣称无损，不把重复提示当作量化修复。
- 更新中英文界面、README 和构建版本。推荐、协议与界面回归结果见下方验证记录。

English: Adds explicit same-27B GSQ-RCO GGUF quantization choices, preserving the existing context and speech budgets. No tiny-model substitution, lossless-quality claim, or automatic change to saved preferences.

Source: [ISTA-DASLab model card and exact files](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF).

## 本次验证 / Validation

- 60 项自动测试通过；打包后的独立程序启动与中英文界面检查通过。
- 已在本机 Ollama 0.40.13、RTX 5080 上完整下载并校验 IQ2_XS（8422841472 字节），通过本地 CLI 导入及 4096 上下文真实加载。
- 使用独立临时数据库的虚构记忆与人格验证通过：主聊天和私有快照均正确复述测试代号；短请求复述实验保留原文并得到算术结果。未使用真实用户聊天或启动语音，临时私有快照已删除，压缩基础模型保留供使用。
- IQ2_S / IQ3_XXS / IQ3_S 仅核对上游文件、GGUF 元数据和自动化兼容路径，未全量下载推理。16K、CPU、其他显卡及与 TTS 同时运行仍需硬件验收；并发语音检查目前是资源预算，不是性能实测。
- 真实短提示实验仅验证可运行与原文保留，没有证明重复可改善量化质量。

English: 60 automated tests and frozen startup checks passed. Full IQ2_XS download/hash/CLI import/4K inference passed on the local RTX 5080, including synthetic approved-memory, persona and private-snapshot recall. Other quantizations, 16K, CPU and concurrent TTS were not tested with full weights. Repetition is not a demonstrated quality improvement.

---

# 0.3.0 容量模式与语音兼容更新

- 大上下文 / 大体量两种资源推荐。
- 为本地语音预留资源，保留 API 选择与原始用户资料。
- 按模型保存上下文，MDC 显式导入 MD 成功部署方案。
- 语音克隆与训练支持核对说明（本次未实现音频上传）。

配套项目：[MDC](https://github.com/reaiksp/ModelDock-Chat) · [MD](https://github.com/reaiksp/ModelDock-Windows)

# ModelDock 0.2.0 · Windows x64 测试版

- 应用内即时切换简体中文 / English，并保存界面语言偏好。
- 单独保存 AI 回复语言设置；遵从明确偏好或跟随用户输入，界面语言不代替回复偏好。
- 保留输入文字与内部用途 / 推荐偏好值，模型名称不被翻译；请求只适配副本，不修改原聊天消息。
- 新增英文 README 与英文界面示例，便携包包含双语资源。
- 20 项自动测试通过，覆盖语言切换的数据保真、CLI、推荐和 HTTP 行为。仍是未签名测试版。

---

# ModelDock 0.1.0 · Windows x64 测试版

可将完整 ZIP 分发给其他 Windows 用户，完整解压后运行 `ModelDock.exe`。

已实现硬件检测、保守模型推荐、Ollama 官方运行环境下载安装与数字签名检查、CLI 模型下载、取消 / 重试、模型加载验证、流式聊天、OpenAI 兼容 API 示例和真实 API 请求验证。

本次验证：

- 推荐规则、HTTP 请求 / 流式响应、错误传播、取消、Windows CLI 重绘进度解析与下载子进程清理自动测试。
- 本机真实硬件检测成功。
- 已安装的 `qwen3.5-9b:latest` 本地模型原生流式聊天返回 `Hello`。
- OpenAI 兼容聊天接口真实请求返回 `OK`，记录见开发目录 `artifacts/api-integration.json`。
- 原生窗口截图已检查。
- 打包后的独立 EXE 启动检查通过，5 个页面可构建，硬件检测与已安装模型列表读取正常。

尚未完成的验收：

- 当前本机访问 Ollama 模型仓库出现 TLS 握手超时，因此新增 `qwen3:0.6b` 的真实下载未完成；程序已返回下载失败，未报告为部署成功。下载解析、退出码校验及取消通过可控子进程测试验证。实际网络通畅时仍需完成整条下载与加载验收。
- 本机已安装 Ollama，尚未在无 Ollama 的干净系统上执行首次自动安装。
- 尚未在不同 AMD / Intel 显卡、低内存设备、企业代理环境及 Windows 10 上验收。
- 本发行包未作代码签名，系统可能提示未知发布者。

发布对象建议先作为测试用户；大范围正式发行前补齐以上验证。软件自身不包含云端服务、遥测或自动上传聊天内容的功能。
