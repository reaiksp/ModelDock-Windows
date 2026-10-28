import logging
import sys
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from modeldock.system import DATA_DIR
from modeldock.ui import STYLE, Window


def main():
    handler = RotatingFileHandler(DATA_DIR / "modeldock.log", maxBytes=2_000_000,
                                  backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("ModelDock")
    app.setOrganizationName("ModelDock")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    def exception_hook(kind, value, tb):
        logging.critical("Unhandled error", exc_info=(kind, value, tb))
        QMessageBox.critical(None, "ModelDock", f"发生错误：{value}\n诊断日志：{DATA_DIR}")
    sys.excepthook = exception_hook
    window = Window()
    if "--smoke-test" in sys.argv:
        target = Path(sys.argv[sys.argv.index("--smoke-test") + 1])
        def check():
            if window.detecting or window.checking:
                QTimer.singleShot(200, check)
                return
            window.i18n.save=None
            window.i18n.set_language("en")
            window.i18n.apply()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"startup": "passed", "frozen": bool(getattr(sys, "frozen", False)),
                "pages": window.stack.count(), "english_ui": "Deployment" in window.nav[0].text(), "hardware_detected": window.hw is not None,
                "models": [m.get("name") for m in window.models]}, ensure_ascii=False, indent=2), "utf-8")
            window.close()
            app.quit()
        QTimer.singleShot(300, check)
    else:
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
