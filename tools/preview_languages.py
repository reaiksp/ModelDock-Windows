import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from modeldock import ui
from modeldock.system import Hardware

app=QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(ui.STYLE)
ui.load_settings=lambda:{'model':'qwen3:4b','usage':'通用对话','preference':'均衡'}
ui.save_settings=lambda data:None
ui.detect=lambda:Hardware('Demo 8-core processor',16,16,12,'Demo GPU 8 GiB',8,200,'C:/Models','')
ui.Window.refresh_service=lambda self:None
window=ui.Window()
window.i18n.save=None
window.ensurePolished()
window.centralWidget().setGeometry(window.rect())
window.layout().activate()
output=Path(__file__).resolve().parents[1]/'artifacts'
output.mkdir(exist_ok=True)

def capture():
    window.i18n.set_language('en')
    window.i18n.apply()
    window.stack.currentWidget().verticalScrollBar().setValue(0)
    QTimer.singleShot(200,save)

def save():
    window.grab().save(str(output/'desktop-en.png'))
    window.close()
    app.quit()
QTimer.singleShot(700,capture)
app.exec()
