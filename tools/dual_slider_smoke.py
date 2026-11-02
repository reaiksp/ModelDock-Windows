"""Native event-loop smoke with synthetic settings/hardware and no downloads.

Run: python tools/dual_slider_smoke.py [report.json]
This process exits normally; it does not suppress native teardown failures.
"""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
temporary = tempfile.TemporaryDirectory(prefix="modeldock-two-slider-")
os.environ["LOCALAPPDATA"] = temporary.name

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from modeldock import ui
from modeldock.i18n import source_text
from modeldock.system import Hardware


app = QApplication([])
for font in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/segoeui.ttf"):
    if Path(font).exists():
        QFontDatabase.addApplicationFont(font)
app.setStyle("Fusion")
app.setStyleSheet(ui.STYLE)
saved = []
initial = {"usage": "压缩大模型", "preference": "质量优先", "model": "existing:latest",
           "capacity": "context", "compression_level": True}
ui.load_settings = lambda: copy.deepcopy(initial)
ui.save_settings = lambda value: saved.append(copy.deepcopy(value))
ui.Window.scan = lambda self: None
ui.Window.refresh_service = lambda self: None
def forbidden(*args, **kwargs):
    raise AssertionError("Slider changes must never call deployment or download")
ui.runtime.one_click = forbidden
window = ui.Window()
window.resize(1180, 850)
window.show()
window.begin_operation = forbidden
window.hw = Hardware("Synthetic CPU", 32, 128, 110, "Synthetic GPU", 24, 500, "E:/synthetic")
result = {"synthetic_settings": True, "synthetic_hardware": True, "real_download": False}
report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "artifacts/dual-slider-source.json"


def check():
    try:
        assert window.compression_slider.minimum() == window.conversation_slider.minimum() == 1
        assert window.compression_slider.maximum() == window.conversation_slider.maximum() == 5
        assert window.compression_slider.value() == 3  # invalid bool does not become level one
        assert window.conversation_slider.value() == 5  # legacy16K requirement maps to the new maximum; active plans stay unchanged
        assert window.capacity.isHidden()
        assert (window.parameter_slider.minimum(), window.parameter_slider.maximum()) == (1, 96)
        for step in range(1, 97):
            window.parameter_slider.setValue(step)
            assert window.settings['parameter_limit'] == step / 2
            assert window.active_model == 'existing:latest'
        window.parameter_slider.setValue(54)
        result['continuous_parameter_range_no_download'] = True

        window.prompt.setPlainText("保持我的原始输入与偏好。")
        for level in range(1, 6):
            window.compression_slider.setValue(level)
            window.conversation_slider.setValue(level)
        assert window.active_model == "existing:latest"
        assert window.prompt.toPlainText() == "保持我的原始输入与偏好。"
        assert saved[-1]["compression_level"] == saved[-1]["conversation_demand"] == 5
        assert window.rec.context == 10240 and len(window.grade_availability) == 5
        result["drag_only_recommends"] = True
        window.voice_budget.setCurrentIndex(window.voice_budget.findData("1.7B"))
        window.conversation_slider.setValue(4)
        assert window.rec.compression_level == 5 and window.rec.effective_compression_level == 2
        assert window.rec.fallback and window.rec.context == 8192
        assert window.compression_slider.value() == 5
        result["requested_and_effective_grade_separate"] = True
        window.usage.setCurrentText("通用对话")
        assert not window.compression_slider.isEnabled() and window.conversation_slider.isEnabled()
        assert window.compression_slider.value() == 5
        window.usage.setCurrentText("压缩大模型")
        window.i18n.set_language("en")
        assert source_text(window.usage) == "压缩大模型"
        assert window.compression_slider.value() == 5 and window.conversation_slider.value() == 4
        assert window.prompt.toPlainText() == "保持我的原始输入与偏好。"
        assert window.active_model == "existing:latest"
        assert "Speech off" in window.plan_comparison.text()
        assert "Current speech budget" in window.plan_comparison.text()
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in window.plan_comparison.text())
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in window.rec_reason.text())
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in window.rec_mode.text())
        # Locale changes invalidate nested height-for-width layouts. Let their
        # queued layout requests settle before checking rendered geometry.
        for _ in range(3):
            app.processEvents()
        available_button = window.compression_availability_button
        assert available_button.height() >= available_button.sizeHint().height()
        slider_card = available_button.parentWidget()
        assert slider_card.height() >= slider_card.layout().heightForWidth(slider_card.width())
        result["localized_card_layout_not_clipped"] = True
        window.i18n.set_language("zh_CN")
        assert "不开语音" in window.plan_comparison.text()
        result["language_preserves_values_and_raw_text"] = True
        window.operation = object()
        window.refresh_slider_labels()
        assert not window.compression_slider.isEnabled() and not window.conversation_slider.isEnabled()
        window.operation = None
        window.refresh_slider_labels()
        assert window.compression_slider.isEnabled() and window.conversation_slider.isEnabled()
        result["busy_disables_both_sliders"] = True
        selected = window.rec.model
        ui.disk_free = lambda path: 500
        # Deliberate deploy action is simulated; no CLI/network operation runs.
        window.begin_operation = lambda *args: None
        window.deploy_recommended()
        assert not window.settings.get("model_plans")
        assert window.pending_plan["compression_level"] == 5
        assert window.pending_plan["effective_compression_level"] == 2
        assert window.pending_plan["conversation_demand"] == 4
        window.deployed(selected.tag.casefold())
        plan = window.settings["model_plans"][selected.tag.casefold()]
        assert plan["context"] == 8192 and plan["usage"] == "压缩大模型"
        assert plan["compression_level"] == 5 and plan["effective_compression_level"] == 2
        assert plan["family"] == "Qwen3.8-27B" and plan["quant"] == "IQ3_XXS"
        result["simulated_success_records_actual_plan"] = True
        result["status"] = "passed"
    except Exception as exc:
        result.update(status="failed", error=str(exc), error_type=type(exc).__name__)
    finally:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        window.close()
        app.quit()


QTimer.singleShot(250, check)
app.exec()
temporary.cleanup()
print(json.dumps(result, ensure_ascii=True), flush=True)
raise SystemExit(0 if result.get("status") == "passed" else 1)
