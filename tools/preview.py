"""Render actual native windows without interacting with the user's desktop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from modeldock.ui import STYLE, Window

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
window = Window()
window.show()
output = Path(__file__).resolve().parents[1] / "artifacts"
output.mkdir(exist_ok=True)

def capture():
    window.stack.currentWidget().verticalScrollBar().setValue(0)
    window.grab().save(str(output / "desktop-preview.png"))
    window.navigate(3)
    QTimer.singleShot(300, capture_api)

def capture_api():
    window.grab().save(str(output / "api-preview.png"))
    window.close()
    app.quit()

QTimer.singleShot(6000, capture)
app.exec()
