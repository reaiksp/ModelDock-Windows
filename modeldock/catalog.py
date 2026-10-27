"""Conservative estimates for Q4 models at a 4096-token context, in GiB."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    tag: str
    title: str
    size: float
    memory: float
    specialty: str
    description: str


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
]


@dataclass(frozen=True)
class Recommendation:
    model: Model | None
    reason: str
    mode: str


def recommend(ram: float, available: float, vram: float, disk: float,
              usage: str = "通用对话", preference: str = "均衡") -> Recommendation:
    # GPU memory and system RAM are deliberately not added together.
    ram_budget = max(0, min(ram - max(3.0, ram * .20), available - 1.0))
    gpu_budget = max(0, vram - max(1.0, vram * .12))
    gpu = gpu_budget >= 1.6 and ram_budget >= 2
    budget = gpu_budget if gpu else ram_budget
    # Keep CPU-only defaults responsive; quality preference may choose larger models.
    if not gpu and preference != "质量优先":
        budget = min(budget, 5.0 if preference == "均衡" else 3.2)
    candidates = [m for m in CATALOG if m.specialty == usage
                  and m.memory <= budget and disk >= m.size * 1.15 + 1]
    mode = "GPU 优先（兼容性以实际加载为准）" if gpu else "CPU / 内存推理"
    if not candidates:
        return Recommendation(None, "可用内存、显存或磁盘不足。请关闭其他程序、释放存储后重新检测。", mode)
    model = candidates[-1]
    if preference == "速度优先" and len(candidates) > 1:
        model = candidates[max(0, len(candidates) - 2)]
    reason = (f"按 4K 上下文估算，运行约需 {model.memory:g} GiB；"
              f"{'显存' if gpu else '内存'}预算 {budget:.1f} GiB，"
              f"下载约 {model.size:.1f} GiB。已预留系统与下载余量。")
    return Recommendation(model, reason, mode)
