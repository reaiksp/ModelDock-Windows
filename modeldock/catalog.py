"""Conservative runtime estimates at 4096 context, in GiB; never model-size promises."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    tag: str
    title: str
    size: float
    memory: float
    specialty: str
    description: str
    source: str = ""
    method: str = ""
    family: str = ""
    quant: str = ""


CATALOG = [
    Model("qwen3:0.6b", "Qwen 3 · 0.6B", .50, 1.8, "通用对话", "入门体验与简单问答，适合低内存电脑。"),
    Model("qwen3:1.7b", "Qwen 3 · 1.7B", 1.31, 3.0, "通用对话", "轻量中文助手，响应快、资源占用低。"),
    Model("qwen3:4b", "Qwen 3 · 4B", 2.33, 4.8, "通用对话", "中文写作、日常问答与轻量推理的均衡选择。"),
    Model("qwen3:8b", "Qwen 3 · 8B", 4.85, 7.5, "通用对话", "更完整的推理与表达能力，适合独立显卡。"),
    Model("qwen3:14b", "Qwen 3 · 14B", 8.67, 12.5, "通用对话", "复杂任务与长文写作，需要更充足的内存。"),
    Model("qwen3:32b", "Qwen 3 · 32B", 18.63, 25.0, "通用对话", "偏重回答质量，适合大显存工作站。"),
    Model("qwen2.5-coder:0.5b", "Qwen Coder · 0.5B", .38, 1.6, "代码开发", "轻量代码补全与语法辅助。"),
    Model("qwen2.5-coder:1.5b", "Qwen Coder · 1.5B", .92, 2.8, "代码开发", "快速代码补全、小型脚本与基础解释。"),
    Model("qwen2.5-coder:3b", "Qwen Coder · 3B", 1.77, 4.4, "代码开发", "轻量编程助手，可在多数电脑上运行。"),
    Model("qwen2.5-coder:7b", "Qwen Coder · 7B", 4.38, 7.0, "代码开发", "代码生成、解释与常见问题修复。"),
    Model("qwen2.5-coder:14b", "Qwen Coder · 14B", 8.38, 12.0, "代码开发", "更复杂的程序理解与代码生成。"),
    Model("qwen2.5-coder:32b", "Qwen Coder · 32B", 18.63, 25.0, "代码开发", "高质量编程任务，适合高配置电脑。"),
    Model("hf.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF:Qwen3.8-27B-GSQ-RCO-IQ2_XS.gguf",
          "Qwen3.8 · 27B · IQ2_XS", 7.9, 10.0, "压缩大模型", "同一 27B 模型的低比特压缩版本，资源需求较低；质量与速度需实际验收。",
          "https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF", "GSQ + RCO", "Qwen3.8-27B", "IQ2_XS"),
    Model("hf.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF:Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf",
          "Qwen3.8 · 27B · IQ2_S", 8.7, 10.8, "压缩大模型", "保留 27B 参数量，采用 IQ2_S 压缩；模型文件大小不等于运行内存。",
          "https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF", "GSQ + RCO", "Qwen3.8-27B", "IQ2_S"),
    Model("hf.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF:Qwen3.8-27B-GSQ-RCO-IQ3_XXS.gguf",
          "Qwen3.8 · 27B · IQ3_XXS", 9.5, 11.5, "压缩大模型", "相同 27B 家族的 IQ3_XXS 档位，需要更充足的可用内存。",
          "https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF", "GSQ + RCO", "Qwen3.8-27B", "IQ3_XXS"),
    Model("hf.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF:Qwen3.8-27B-GSQ-RCO-IQ3_S.gguf",
          "Qwen3.8 · 27B · IQ3_S", 11.0, 13.0, "压缩大模型", "同家族较高位宽档位，偏向质量取舍；仍可能有量化误差。",
          "https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF", "GSQ + RCO", "Qwen3.8-27B", "IQ3_S"),
]


def resource_budget(ram, available, vram, voice="off"):
    """Do not add RAM to VRAM; reserve host memory and managed speech resources."""
    ram_budget = max(0, min(ram - max(3.0, ram * .20), available - 1.0))
    gpu_budget = max(0, vram - max(1.0, vram * .12))
    vg, vr = {"0.6B": (4.0, 4.0), "1.7B": (7.0, 5.0)}.get(voice, (0.0, 0.0))
    if vg and (gpu_budget < vg + 1.6 or ram_budget < vr + 2):
        return 0.0, "GPU", False
    gpu_budget -= vg
    ram_budget -= vr
    gpu = gpu_budget >= 1.6 and ram_budget >= 2
    return (gpu_budget if gpu else ram_budget), ("GPU" if gpu else "CPU"), True


def deployment_disk(model):
    """Compressed import may retain both the verified GGUF cache and an Ollama blob."""
    return model.size * (2.15 if model.method else 1.15) + 1


def fits_model(model, ram, available, vram, disk, context=4096, voice="off"):
    """Use the same context/speech resource checks for manual and recommended models."""
    budget, _, valid = resource_budget(ram, available, vram, voice)
    return valid and model.memory + (4.0 if context > 4096 else 0.0) <= budget and disk >= deployment_disk(model)


@dataclass(frozen=True)
class Recommendation:
    model: Model | None
    reason: str
    mode: str
    context: int = 4096


def recommend(ram: float, available: float, vram: float, disk: float,
              usage: str = "通用对话", preference: str = "均衡", profile="large", voice="off") -> Recommendation:
    # GPU memory and system RAM are deliberately not added together.
    context = 16384 if profile == "context" else 4096
    extra = 4.0 if context > 4096 else 0.0
    budget, device, valid = resource_budget(ram, available, vram, voice)
    if not valid:
        return Recommendation(None, "语音与文字同时运行资源不足。", "GPU", context)
    gpu = device == "GPU"
    # Keep CPU-only defaults responsive; quality preference may choose larger models.
    if not gpu and preference != "质量优先":
        budget = min(budget, (5.0 if preference == "均衡" else 3.2) + extra)
    candidates = [m for m in CATALOG if m.specialty == usage
                  and m.memory + extra <= budget and disk >= deployment_disk(m)]
    candidates.sort(key=lambda m: (m.memory, m.size))
    mode = "GPU 优先（兼容性以实际加载为准）" if gpu else "CPU / 内存推理"
    if not candidates:
        if usage == "压缩大模型":
            return Recommendation(None, "当前预算或偏好不适合该压缩大模型方案；不会自动改成小参数模型。CPU 用户可选择质量优先，但生成可能很慢。", mode, context)
        return Recommendation(None, "可用内存、显存或磁盘不足。请关闭其他程序、释放存储后重新检测。", mode, context)
    model = candidates[-1]
    if preference == "速度优先" and len(candidates) > 1:
        model = candidates[max(0, len(candidates) - 2)]
    reason = (f"按 4K 上下文估算，运行约需 {model.memory:g} GiB；"
              f"{'显存' if gpu else '内存'}预算 {budget:.1f} GiB，"
              f"下载约 {model.size:.1f} GiB。已预留系统与下载余量。")
    notes = (" 16K 上下文额外预留 4 GiB。" if extra else "") + (" 已为本地语音预留资源。" if voice in {"0.6B", "1.7B"} else "")
    if model.method:
        notes += " 同一 27B 模型的不同量化档位，不是更小参数模型；压缩可能影响质量。"
        if not gpu:
            notes += " CPU 大模型推理可能很慢。"
    return Recommendation(model, reason + notes, mode, context)
