import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from modeldock import ui
from modeldock.i18n import source_text

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
