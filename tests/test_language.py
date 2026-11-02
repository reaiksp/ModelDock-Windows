import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from modeldock import ui
from modeldock.i18n import source_text

REFRESH_SERVICE = ui.Window.refresh_service

@pytest.fixture
def window(monkeypatch):
    app=QApplication.instance() or QApplication([])
    settings={'usage':'代码开发','preference':'速度优先','model':'通用对话','response_language':'en'}
    saved=[]
    monkeypatch.setattr(ui,'load_settings',lambda:dict(settings))
    monkeypatch.setattr(ui,'save_settings',lambda data:saved.append(data))
    monkeypatch.setattr(ui.Window,'scan',lambda self:None)
    monkeypatch.setattr(ui.Window,'refresh_service',lambda self:None)
    win=ui.Window()
    yield win,saved
    win.timer.stop()
    win.close()


def test_md_language_switch_preserves_internal_values_user_model_and_draft(window):
    win,saved=window
    win.local_combo.addItem('通用对话')
    win.prompt.setPlainText('保存人格 user input')
    win.i18n.set_language('en')
    assert win.nav[0].text()=='◫   Deployment'
    assert win.usage.currentText()=='Coding'
    assert source_text(win.usage)=='代码开发'
    assert source_text(win.preference)=='速度优先'
    assert win.local_combo.currentText()=='通用对话'
    assert win.prompt.toPlainText()=='保存人格 user input'
    assert win.reply_language.currentData()=='en'
    assert saved[-1]['usage']=='代码开发' and saved[-1]['ui_language']=='en'
    win.i18n.set_language('zh_CN')
    assert win.usage.currentText()=='代码开发'
    assert win.prompt.toPlainText()=='保存人格 user input'
    assert win.reply_language.currentData()=='en'


def test_deployed_plan_uses_actual_model_name_and_preserves_alias_data(window):
    win, saved = window
    alias = "hf.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF:Qwen3.8-27B-GSQ-RCO-IQ2_XS.gguf"
    actual = alias.casefold()
    old = {"model": alias, "context": 4096, "custom_user_option": "keep this"}
    other = {"model": "other", "context": 16384}
    win.settings["model_plans"] = {alias: dict(old), "other": dict(other)}
    win.pending_plan = {"model": alias, "context": 16384, "capacity": "context", "voice": "off"}
    win.deployed(actual)
    assert win.active_model == actual and win.pending_plan["model"] == actual
    assert alias not in win.settings["model_plans"]
    plan = win.settings["model_plans"][actual]
    assert plan["model"] == actual and plan["context"] == 16384
    assert plan["custom_user_option"] == "keep this"
    assert win.settings["model_plan_aliases"][alias] == old
    assert win.settings["model_plans"]["other"] == other
    assert saved[-1]["model"] == actual


def test_refresh_recognizes_hf_name_case_and_migrates_plan(window, monkeypatch):
    win, saved = window
    alias = "hf.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF:Qwen3.8-27B-GSQ-RCO-IQ2_S.gguf"
    actual = alias.casefold()
    win.active_model = alias
    win.settings["model_plans"] = {alias: {"model": alias, "context": 16384}}
    win.checking = False
    monkeypatch.setattr(ui.runtime, "status", lambda: "test")
    monkeypatch.setattr(ui.runtime, "installed", lambda: [{"name": "other:latest"}, {"name": actual}])
    class Signal:
        def connect(self, fn):
            fn()
    class Job:
        finished = Signal()
    def launch(fn, done, failed):
        done(fn(None))
        return Job()
    monkeypatch.setattr(win, "launch", launch)
    REFRESH_SERVICE(win)
    assert win.active_model == actual and win.local_combo.currentText() == actual
    assert win.settings["model_plans"][actual]["model"] == actual
    assert win.settings["model_plans"][actual]["context"] == 16384
    assert alias not in win.settings["model_plans"]
