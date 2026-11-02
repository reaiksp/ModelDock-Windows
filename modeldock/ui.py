import json
import logging
import threading
import time
from dataclasses import asdict

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSlider, QStackedWidget, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from . import __version__, runtime
from .catalog import CATALOG, COMPRESSION_LEVELS, CONVERSATION_LEVELS, deployment_disk, fits_model, recommend
from .i18n import LanguageManager, source_text, tr
from .system import DATA_DIR, detect, disk_free, find_ollama, load_settings, save_settings


STYLE = """
QWidget {font-family:'Microsoft YaHei UI','Segoe UI'; font-size:13px; color:#243440;}
QMainWindow, QStackedWidget {background:#f4f7f8;}
QFrame#sidebar {background:#142c31;}
QLabel#brand {color:#f3fffc; font-size:24px; font-weight:700;}
QLabel#sideMuted {color:#92afb2; font-size:12px;}
QLabel#sideStatus {color:#a3eed0; background:#234148; padding:12px; border-radius:8px;}
QPushButton#nav {text-align:left; border:0; color:#b5cacc; background:transparent; padding:14px 18px; border-radius:8px; font-size:14px;}
QPushButton#nav:checked {background:#2a4c50; color:#e9fff7; font-weight:600;}
QPushButton#nav:hover {background:#234147;}
QLabel#eyebrow {color:#578278; font-size:11px; font-weight:700;}
QLabel#title {font-size:28px; font-weight:700; color:#19343a;}
QLabel#muted {color:#71848c;}
QLabel#section {font-size:16px; font-weight:700;}
QLabel#metric {font-size:22px; font-weight:700; color:#193d40;}
QLabel#heroTitle {font-size:27px; font-weight:700; color:#173d36;}
QLabel#badge {color:#1a7057; background:#dbf3e8; padding:5px 10px; border-radius:5px; font-size:11px;}
QFrame#card {background:white; border:1px solid #e0e8ea; border-radius:12px;}
QFrame#hero {background:#e8f5ef; border:1px solid #cce6da; border-radius:12px;}
QPushButton {background:white; border:1px solid #d6e0e3; border-radius:7px; padding:9px 15px; font-weight:500;}
QPushButton:hover {background:#eaf3f0; border-color:#a2c6b9;}
QPushButton:disabled {color:#9caeaf; background:#e6edeb; border-color:#e0e7e5;}
QPushButton#primary {background:#167b60; color:white; border:1px solid #167b60; font-weight:600;}
QPushButton#primary:hover {background:#11694f;}
QPushButton#primary:disabled {background:#a1bdb4; border-color:#a1bdb4;}
QComboBox,QDoubleSpinBox {background:white; border:1px solid #d8e3e4; border-radius:6px; padding:8px; min-height:20px;}
QPlainTextEdit, QTextEdit {background:#f8fafb; border:1px solid #dfe7e9; border-radius:8px; padding:10px; selection-background-color:#b6e6d5;}
QPlainTextEdit#code {background:#172e35; color:#cee9e0; font-family:Consolas; font-size:12px; border:0;}
QProgressBar {background:#dce9e4; border:0; border-radius:4px; height:8px; text-align:center;}
QProgressBar::chunk {background:#1b956f; border-radius:4px;}
QScrollArea {border:0; background:transparent;}
QScrollArea > QWidget > QWidget {background:transparent;}
QTabWidget::pane {border:0;}
QTabBar::tab {padding:10px 18px; background:#e8efef; margin:0 4px 6px 0; border-radius:5px;}
QTabBar::tab:selected {background:#d2eadd; color:#16694f;}
QToolTip {background:#193d40; color:white; padding:6px;}
"""


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    return widget


def card(name="card"):
    frame = QFrame()
    frame.setObjectName(name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    return frame, layout


class Job(QObject):
    success = Signal(object)
    failure = Signal(str)
    finished = Signal()
    log = Signal(str)
    progress = Signal(int, str)
    token = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.task = runtime.Task()
        self.fn = fn

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            self.success.emit(self.fn(self))
        except runtime.Cancelled as exc:
            self.failure.emit(str(exc))
        except Exception as exc:
            logging.exception("Background operation failed")
            self.failure.emit(str(exc))
        finally:
            self.finished.emit()


def app_icon():
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#167b60"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, 64, 64, 15, 15)
    painter.setPen(QColor("white"))
    painter.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "M")
    painter.end()
    return QIcon(pix)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"ModelDock · 本地模型工作台 {__version__}")
        self.setWindowIcon(app_icon())
        area = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(940, 640)
        self.resize(min(1180, area.width() - 40), min(850, area.height() - 40))
        self.hw = None
        self.models = []
        self.jobs = set()
        self.operation = None
        self.chat_job = None
        self.checking = False
        self.detecting = False
        self.messages = []
        self.answer = ""
        self.settings = load_settings()
        self.active_model = self.settings.get("model", "")
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(214)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 30, 18, 24)
        side.setSpacing(8)
        side.addWidget(label("◈  ModelDock", "brand"))
        side.addWidget(label("你的模型，在你的电脑上。", "sideMuted"))
        side.addSpacing(32)
        self.nav = []
        for index, title in enumerate(["◫   部署工作台", "▦   模型中心", "◌   本地对话", "⌘   API 接入", "≡   运行日志"]):
            nav = button(title, lambda checked=False, i=index: self.navigate(i))
            nav.setObjectName("nav")
            nav.setCheckable(True)
            side.addWidget(nav)
            self.nav.append(nav)
        side.addSpacing(12)
        side.addWidget(label("Language / 语言", "sideMuted"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("简体中文", "zh_CN")
        self.language_combo.addItem("English", "en")
        self.language_combo.setProperty('_i18n_skip', True)
        side.addWidget(self.language_combo)
        side.addStretch()
        self.side_status = label("●  正在检查服务…", "sideStatus", True)
        side.addWidget(self.side_status)
        side.addSpacing(12)
        side.addWidget(label(f"WINDOWS DESKTOP\n版本 {__version__} · 本地优先", "sideMuted"))
        layout.addWidget(sidebar)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.build_home()
        self.build_models()
        self.build_chat()
        self.build_api()
        self.build_logs()
        self.local_combo.setProperty('_i18n_user_items', True)
        self.chat_model.setProperty('_i18n_skip', True)
        self.i18n = LanguageManager(self, self.settings.get('ui_language','zh_CN'), self.save_language)
        self.language_combo.setCurrentIndex(max(0,self.language_combo.findData(self.i18n.language)))
        self.language_combo.currentIndexChanged.connect(lambda: self.i18n.set_language(self.language_combo.currentData()))
        self.i18n.changed.connect(self.language_changed)
        self.i18n.apply()
        self.refresh_slider_labels()
        self.navigate(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_service)
        self.timer.start(12000)
        QTimer.singleShot(100, self.scan)
        QTimer.singleShot(150, self.refresh_service)

    def save_language(self, language):
        self.settings['ui_language'] = language
        self.persist()

    def save_reply_language(self):
        self.settings['response_language'] = self.reply_language.currentData()
        self.persist()

    def language_changed(self, language):
        blocked = self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(self.language_combo.findData(language))
        self.language_combo.blockSignals(blocked)
        if self.hw:
            self.update_recommendation()
        else:
            self.refresh_slider_labels()
        if self.messages or self.chat_job:
            self.render_chat()

    def page(self, eyebrow, title, subtitle):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        box = QVBoxLayout(body)
        box.setContentsMargins(34, 28, 34, 28)
        box.setSpacing(18)
        box.addWidget(label(eyebrow, "eyebrow"))
        box.addWidget(label(title, "title"))
        box.addWidget(label(subtitle, "muted", True))
        scroll.setWidget(body)
        self.stack.addWidget(scroll)
        return box

    def navigate(self, index):
        self.stack.setCurrentIndex(index)
        for i, nav in enumerate(self.nav):
            nav.setChecked(i == index)

    def launch(self, fn, success=None, failure=None):
        job = Job(fn)
        self.jobs.add(job)
        job.log.connect(self.log)
        if success:
            job.success.connect(success)
        job.failure.connect(failure or self.error)
        job.finished.connect(lambda: self.jobs.discard(job))
        # Start on the next event-loop tick so callers can connect all signals first.
        QTimer.singleShot(0, job.start)
        return job

    def log(self, message):
        text = f"{time.strftime('%H:%M:%S')}  {message}"
        self.log_view.appendPlainText(text)
        logging.info(message)

    def error(self, message):
        self.log(message)
        QMessageBox.warning(self, "操作提示", message)

    def build_home(self):
        box = self.page("LOCAL AI / DEPLOYMENT", "让本地 AI，开箱即用", "检测配置 → 智能选型 → 下载部署。把命令行的能力，变成一个按钮。")
        row = QHBoxLayout()
        row.addWidget(label("01  /  这台电脑", "section"))
        row.addStretch()
        self.scan_button = button("↻  重新检测", self.scan)
        row.addWidget(self.scan_button)
        box.addLayout(row)
        metrics = QHBoxLayout()
        self.metric_labels = []
        for title in ["处理器", "系统内存", "显卡 / 空闲显存", "模型盘可用空间"]:
            frame, col = card()
            col.addWidget(label(title, "muted"))
            value = label("检测中…", "metric", True)
            value.setMinimumHeight(52)
            col.addWidget(value)
            metrics.addWidget(frame, 1)
            self.metric_labels.append(value)
        box.addLayout(metrics)
        self.hardware_note = label("正在读取这台电脑的实际配置…", "muted", True)
        box.addWidget(self.hardware_note)
        config = QHBoxLayout()
        config.addWidget(label("主要用途"))
        self.usage = QComboBox()
        self.usage.addItems(["通用对话", "代码开发", "压缩大模型"])
        self.usage.setCurrentText(self.settings.get("usage", "通用对话"))
        config.addWidget(self.usage, 1)
        config.addWidget(label("推荐偏好"))
        self.preference = QComboBox()
        self.preference.addItems(["均衡", "速度优先", "质量优先"])
        self.preference.setCurrentText(self.settings.get("preference", "均衡"))
        config.addWidget(self.preference, 1)
        box.addLayout(config)
        row = QHBoxLayout()
        self.capacity = QComboBox()
        for title, value in [("大体量 · 4K 上下文", "large"), ("大上下文 · 16K", "context")]:
            self.capacity.addItem(title, value)
        self.capacity.setCurrentIndex(max(0,self.capacity.findData(self.settings.get("capacity","large"))))
        row.addWidget(self.capacity)
        self.capacity.hide()  # Legacy setting remains readable; the second slider controls new plans.
        self.voice_budget = QComboBox()
        for title, value in [("不开语音 / API 语音", "off"), ("本地语音 0.6B", "0.6B"), ("本地语音 1.7B", "1.7B")]:
            self.voice_budget.addItem(title,value)
        self.voice_budget.setCurrentIndex(max(0,self.voice_budget.findData(self.settings.get("voice_budget","off"))))
        row.addWidget(self.voice_budget)
        box.addLayout(row)
        controls, sliders = card()
        sliders.addWidget(label("精简与完全体 · 同一模型的五档精度", "section"))
        ends = QHBoxLayout()
        ends.addWidget(label("精简省资源", "muted"))
        ends.addStretch()
        ends.addWidget(label("BF16 完全体", "muted"))
        sliders.addLayout(ends)
        self.compression_slider = QSlider(Qt.Orientation.Horizontal)
        self.compression_slider.setRange(1, 5)
        self.compression_slider.setSingleStep(1)
        self.compression_slider.setPageStep(1)
        self.compression_slider.setTickInterval(1)
        self.compression_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.compression_slider.setValue(self.saved_level("compression_level", 3))
        sliders.addWidget(self.compression_slider)
        self.compression_label = label("", "muted", True)
        self.compression_label.setProperty('_i18n_skip', True)
        sliders.addWidget(self.compression_label)
        sliders.addWidget(label("对话长短与记忆需求", "section"))
        ends = QHBoxLayout()
        ends.addWidget(label("短聊 · 基础记忆", "muted"))
        ends.addStretch()
        ends.addWidget(label("长聊 · 记忆优先", "muted"))
        sliders.addLayout(ends)
        self.conversation_slider = QSlider(Qt.Orientation.Horizontal)
        self.conversation_slider.setRange(1, 5)
        self.conversation_slider.setSingleStep(1)
        self.conversation_slider.setPageStep(1)
        self.conversation_slider.setTickInterval(1)
        self.conversation_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.conversation_slider.setValue(self.saved_level("conversation_demand", 4 if self.settings.get("capacity") == "context" else 2))
        sliders.addWidget(self.conversation_slider)
        self.conversation_label = label("", "muted", True)
        self.conversation_label.setProperty('_i18n_skip', True)
        sliders.addWidget(self.conversation_label)
        self.grade_availability = []
        self.compression_availability_button = button("查看五档可用性", self.toggle_grade_availability)
        sliders.addWidget(self.compression_availability_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.compression_availability = label("", "muted", True)
        self.compression_availability.setProperty('_i18n_skip', True)
        self.compression_availability.hide()
        sliders.addWidget(self.compression_availability)
        sliders.addWidget(label("拖动只分析推荐，不下载或切换模型。记忆需求影响上下文与资源预留，不保证记忆准确率。", "muted", True))
        box.addWidget(controls)
        self.plan_comparison = label("", "muted", True)
        box.addWidget(self.plan_comparison)
        box.addWidget(button("打开配套聊天 MDC ↗", lambda: QDesktopServices.openUrl(QUrl("https://github.com/reaiksp/ModelDock-Chat"))))
        self.capacity.currentIndexChanged.connect(self.update_recommendation)
        self.compression_slider.valueChanged.connect(self.update_recommendation)
        self.conversation_slider.valueChanged.connect(self.update_recommendation)
        self.voice_budget.currentIndexChanged.connect(self.update_recommendation)
        self.usage.currentTextChanged.connect(self.update_recommendation)
        self.preference.currentTextChanged.connect(self.update_recommendation)
        frame, hero = card("hero")
        top = QHBoxLayout()
        top.addWidget(label("02  /  为这台电脑推荐", "section"))
        top.addStretch()
        self.rec_badge = label("自动适配 · 4K 上下文", "badge")
        top.addWidget(self.rec_badge)
        hero.addLayout(top)
        self.rec_title = label("正在分析最合适的模型…", "heroTitle")
        self.rec_reason = label("首次部署会下载运行环境及模型文件，请保持网络连接。", "muted", True)
        self.rec_mode = label("", "muted")
        hero.addWidget(self.rec_title)
        hero.addWidget(self.rec_reason)
        hero.addWidget(self.rec_mode)
        actions = QHBoxLayout()
        self.deploy_button = button("↓  一键推荐并部署", self.deploy_recommended, True)
        self.deploy_button.setEnabled(False)
        actions.addWidget(self.deploy_button)
        actions.addWidget(button("浏览全部模型  →", lambda: self.navigate(1)))
        actions.addStretch()
        hero.addLayout(actions)
        box.addWidget(frame)
        progress_frame, progress_layout = card()
        self.task_title = label("03  /  准备就绪", "section")
        self.task_detail = label("部署后即可在本地对话，也可通过 API 接入自己的应用。", "muted", True)
        progress_layout.addWidget(self.task_title)
        progress_layout.addWidget(self.task_detail)
        bar_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        bar_row.addWidget(self.progress, 1)
        self.cancel_button = button("取消任务", self.cancel_operation)
        self.cancel_button.setEnabled(False)
        bar_row.addWidget(self.cancel_button)
        progress_layout.addLayout(bar_row)
        box.addWidget(progress_frame)
        self.install_button = button("安装 / 检查 Ollama 运行环境", self.install)
        box.addWidget(self.install_button, alignment=Qt.AlignmentFlag.AlignLeft)
        box.addWidget(label("常规模型经 Ollama CLI 下载；压缩大模型固定版本下载、校验后经 CLI 导入。体积与内存为估算，实际以加载结果为准。", "muted", True))
        box.addStretch()

    def scan(self):
        if self.detecting:
            return
        self.detecting = True
        self.scan_button.setEnabled(False)
        def complete(hw):
            self.hw = hw
            self.metric_labels[0].setText(f"{hw.cores} 线程")
            self.metric_labels[0].setToolTip(hw.cpu)
            self.metric_labels[1].setText(f"{hw.ram:.0f} GiB")
            self.metric_labels[1].setToolTip(f"当前可用 {hw.available:.1f} GiB")
            self.metric_labels[2].setText(f"{hw.vram:.1f} GiB" if hw.vram else "CPU 方案")
            self.metric_labels[2].setToolTip(hw.gpu)
            self.metric_labels[3].setText(f"{hw.disk:.0f} GiB")
            self.metric_labels[3].setToolTip(hw.models_path)
            self.hardware_note.setText(f"{hw.cpu}  /  {hw.gpu}\n{hw.note}")
            self.update_recommendation()
            self.log("硬件检测完成。" + hw.note)
        job = self.launch(lambda j: detect(), complete)
        job.finished.connect(self.scan_finished)

    def scan_finished(self):
        self.detecting = False
        self.scan_button.setEnabled(True)

    def saved_level(self, key, default):
        value = self.settings.get(key, default)
        return value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5 else default

    def toggle_grade_availability(self):
        self.compression_availability.setVisible(not self.compression_availability.isVisible())

    def refresh_slider_labels(self):
        if not hasattr(self, "compression_slider"):
            return
        level = self.compression_slider.value()
        title, quant = COMPRESSION_LEVELS[level]
        applicable = source_text(self.usage) == "压缩大模型"
        self.compression_slider.setEnabled(applicable and self.operation is None)
        self.conversation_slider.setEnabled(self.operation is None)
        self.compression_availability_button.setEnabled(applicable)
        self.compression_label.setText(tr("目标 {0}/5 · {1} · {2}").format(level, tr(title), quant) if applicable else tr("此用途保持现有模型；精度五档仅适用于同一压缩大模型，选择已保留。"))
        demand = self.conversation_slider.value()
        title, context = CONVERSATION_LEVELS[demand]
        self.conversation_label.setText(tr("需求 {0}/5 · {1} · {2} tokens").format(demand, tr(title), context))
        self.compression_availability.setText("\n".join(
            tr("{0} 档 · {1} · {2}").format(level, COMPRESSION_LEVELS[level][1], tr("可用" if available else "资源不足"))
            for level, available in self.grade_availability) if self.grade_availability else tr("检测硬件并选择压缩大模型后显示五档可用性。"))

    def update_recommendation(self):
        level, demand = self.compression_slider.value(), self.conversation_slider.value()
        self.settings.update(compression_level=level, conversation_demand=demand, voice_budget=self.voice_budget.currentData())
        legacy = "context" if CONVERSATION_LEVELS[demand][1] >= 16384 else "large"
        blocked = self.capacity.blockSignals(True)
        self.capacity.setCurrentIndex(self.capacity.findData(legacy))
        self.capacity.blockSignals(blocked)
        self.settings["capacity"] = legacy
        self.refresh_slider_labels()
        if not self.hw:
            self.persist()
            return
        self.rec = recommend(self.hw.ram, self.hw.available, self.hw.vram, self.hw.disk,
                             source_text(self.usage), source_text(self.preference), self.capacity.currentData(), self.voice_budget.currentData(), level, demand)
        self.grade_availability = []
        if source_text(self.usage) == "压缩大模型":
            for item in range(1, 6):
                choice = recommend(self.hw.ram, self.hw.available, self.hw.vram, self.hw.disk,
                    "压缩大模型", source_text(self.preference), legacy, self.voice_budget.currentData(), item, demand)
                self.grade_availability.append((item, choice.effective_compression_level == item))
        self.refresh_slider_labels()
        comparisons = []
        for title, voice in [(tr("不开语音"), "off"), (tr("当前语音预算"), self.voice_budget.currentData())]:
            plan = recommend(self.hw.ram,self.hw.available,self.hw.vram,self.hw.disk,source_text(self.usage),source_text(self.preference),legacy,voice,level,demand)
            comparisons.append(f"{title}: {plan.model.title if plan.model else tr('资源不足')} / {plan.context}")
        self.plan_comparison.setText("\n".join(comparisons))
        self.rec_badge.setText(f"{self.rec.context} tokens")
        self.settings.update(capacity=self.capacity.currentData(), voice_budget=self.voice_budget.currentData())
        self.rec_title.setText(self.rec.model.title if self.rec.model else "暂时没有安全的推荐")
        self.rec_reason.setText(tr(self.rec.reason))
        self.rec_mode.setText(tr(self.rec.mode))
        self.deploy_button.setEnabled(bool(self.rec.model) and self.operation is None)
        self.persist()

    def persist(self):
        try:
            save_settings(dict(self.settings, usage=source_text(self.usage), preference=source_text(self.preference), model=self.active_model))
        except OSError as exc:
            self.log(f"偏好保存失败：{exc}")

    def build_models(self):
        box = self.page("MODEL LIBRARY", "找到你的下一位助手", "精选本地文字模型 · 通用对话与代码开发 · 下载由 Ollama CLI 执行")
        installed_frame, local = card()
        row = QHBoxLayout()
        row.addWidget(label("已安装模型", "section"))
        row.addStretch()
        row.addWidget(button("刷新列表", self.refresh_service))
        local.addLayout(row)
        self.local_combo = QComboBox()
        self.local_combo.currentTextChanged.connect(self.select_model)
        local.addWidget(self.local_combo)
        local.addWidget(label("选择后用于本地对话和 API 示例。模型文件保留在 Ollama 的模型目录。", "muted", True))
        box.addWidget(installed_frame)
        grid = QGridLayout()
        self.model_buttons = []
        for index, model in enumerate(CATALOG):
            frame, col = card()
            row = QHBoxLayout()
            row.addWidget(label(model.specialty, "badge"))
            row.addStretch()
            row.addWidget(label(f"≈ {model.size:.1f} GiB", "muted"))
            col.addLayout(row)
            col.addWidget(label(model.title, "section"))
            col.addWidget(label(model.description, "muted", True))
            col.addWidget(label(f"4K 运行预算 ≈ {model.memory:g} GiB", "muted"))
            if model.method:
                col.addWidget(label(f"{model.family} · {model.method} · {model.quant}", "muted", True))
                col.addWidget(label("压缩导入需预留缓存与模型双份空间。", "muted", True))
                col.addWidget(button("压缩模型来源与说明 ↗", lambda checked=False, url=model.source: QDesktopServices.openUrl(QUrl(url))))
            btn = button("下载并部署", lambda checked=False, m=model: self.start_deploy(m.tag, m.size, m.memory, CONVERSATION_LEVELS[self.conversation_slider.value()][1], self.capacity.currentData(), self.voice_budget.currentData()))
            col.addWidget(btn)
            self.model_buttons.append(btn)
            grid.addWidget(frame, index // 2, index % 2)
        box.addLayout(grid)
        box.addStretch()

    def refresh_service(self):
        if self.checking:
            return
        self.checking = True
        def fetch(j):
            version = runtime.status()
            return version, runtime.installed() if version else []
        def complete(result):
            version, self.models = result
            self.side_status.setText(f"●  Ollama {version}\n本地服务在线" if version else "○  服务未启动\n部署时自动启动")
            names = [m.get("name", "") for m in self.models]
            self.local_combo.blockSignals(True)
            self.local_combo.clear()
            self.local_combo.addItems(names)
            selected = next((name for name in names if runtime.model_key(name) == runtime.model_key(self.active_model)), None)
            changed = self.adopt_model_name(selected if selected is not None else (names[0] if names else ""))
            self.local_combo.setCurrentText(self.active_model)
            self.local_combo.blockSignals(False)
            self.chat_model.setText(self.active_model or "尚无可用模型，请先部署")
            self.update_api()
            if changed:
                self.persist()
        job = self.launch(fetch, complete, lambda msg: self.log(msg))
        job.finished.connect(lambda: setattr(self, "checking", False))

    def adopt_model_name(self, actual):
        """Use Ollama's returned spelling and migrate matching plan aliases losslessly."""
        changed = self.active_model != actual
        self.active_model = actual
        if not actual:
            return changed
        plans = self.settings.setdefault("model_plans", {})
        aliases = [name for name in plans if name != actual and runtime.model_key(name) == runtime.model_key(actual)]
        for alias in aliases:
            previous = plans.pop(alias)
            # Preserve the exact old value in case aliases held conflicting options.
            archive = self.settings.setdefault("model_plan_aliases", {})
            backup, revision = alias, 2
            while backup in archive and archive[backup] != previous:
                backup = alias + "#" + str(revision)
                revision += 1
            archive[backup] = previous
            if isinstance(previous, dict):
                merged = dict(previous)
                merged.update(plans.get(actual, {}))
                merged["model"] = actual
                plans[actual] = merged
            changed = True
        if isinstance(plans.get(actual), dict) and plans[actual].get("model") != actual:
            plans[actual] = dict(plans[actual], model=actual)
            changed = True
        return changed

    def select_model(self, name):
        if self.chat_job:
            self.local_combo.blockSignals(True)
            self.local_combo.setCurrentText(self.active_model)
            self.local_combo.blockSignals(False)
            return
        self.active_model = name
        self.clear_chat()
        self.chat_model.setText(name or "尚无可用模型，请先部署")
        self.update_api()
        self.persist()

    def deploy_recommended(self):
        if self.hw and self.rec.model:
            m = self.rec.model
            self.start_deploy(m.tag, m.size, m.memory, self.rec.context, self.capacity.currentData(), self.voice_budget.currentData())

    def start_deploy(self, tag, size, memory, context=4096, profile="large", voice="off"):
        if self.operation:
            return
        if self.chat_job:
            self.error("请先停止当前对话生成，再部署其他模型。")
            return
        if not self.hw:
            self.error("请先完成配置检测，再部署模型。")
            return
        model = next((m for m in CATALOG if runtime.model_key(m.tag) == runtime.model_key(tag)), None)
        required_disk = deployment_disk(model) if model else size * 1.15 + 1
        try:
            free = disk_free(self.hw.models_path if self.hw else runtime.model_dir())
            if free < required_disk:
                raise RuntimeError(f"模型存储盘仅剩 {free:.1f} GiB，建议至少 {required_disk:.1f} GiB。")
        except OSError as exc:
            self.error(f"无法检查模型存储盘：{exc}")
            return
        except RuntimeError as exc:
            self.error(str(exc))
            return
        if model and not fits_model(model, self.hw.ram, self.hw.available, self.hw.vram, free, context, voice):
            self.error("当前模型、上下文与语音组合超过可用预算，请选择更低位宽、关闭本地语音或重新检测。")
            return
        self.navigate(0)
        self.task_title.setText(f"03  /  正在部署 {tag}")
        demand = self.conversation_slider.value()
        if CONVERSATION_LEVELS[demand][1] != context:
            demand = {4096: 2, 8192: 3, 16384: 4, 32768: 5}.get(context, demand)
        self.pending_plan = dict(model=tag, context=context, capacity=profile, voice=voice,
            conversation_demand=demand, usage=model.specialty if model else source_text(self.usage),
            compression_level=self.compression_slider.value() if model and model.specialty == "压缩大模型" else None,
            effective_compression_level=(model.compression_level or None) if model else None,
            family=model.family if model else "", quant=model.quant if model else "")
        self.begin_operation(lambda j: runtime.one_click(tag, j.task, j.log.emit, j.progress.emit, context), self.deployed)

    def begin_operation(self, fn, success):
        if self.operation:
            return
        self.progress.setRange(0, 0)
        self.task_detail.setText("正在准备，请稍候…")
        self.deploy_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.compression_slider.setEnabled(False)
        self.conversation_slider.setEnabled(False)
        for btn in self.model_buttons:
            btn.setEnabled(False)
        def failed(message):
            self.task_title.setText("03  /  操作已停止")
            self.task_detail.setText(message)
            self.log(message)
        self.operation = self.launch(fn, success, failed)
        self.operation.progress.connect(self.on_progress)
        self.operation.log.connect(self.task_detail.setText)
        self.operation.finished.connect(self.operation_finished)

    def on_progress(self, value, detail):
        self.progress.setRange(0, 0 if value < 0 else 100)
        if value >= 0:
            self.progress.setValue(value)
        self.task_detail.setText(detail)

    def operation_finished(self):
        self.operation = None
        self.progress.setRange(0, 100)
        self.cancel_button.setEnabled(False)
        self.install_button.setEnabled(True)
        for btn in self.model_buttons:
            btn.setEnabled(True)
        self.update_recommendation()
        self.refresh_service()

    def cancel_operation(self):
        if self.operation:
            self.operation.task.cancel()
            self.cancel_button.setEnabled(False)
            self.task_detail.setText("正在取消，请稍候…")

    def deployed(self, tag):
        self.clear_chat()
        self.adopt_model_name(tag)
        self.pending_plan = dict(self.pending_plan, model=tag)
        plan = dict(self.settings.setdefault("model_plans", {}).get(tag, {}))
        plan.update(self.pending_plan)
        self.settings["model_plans"][tag] = plan
        self.task_title.setText("03  /  部署完成 ✓")
        self.task_detail.setText(f"{tag} 已加载。前往“本地对话”体验，或复制 API 示例开始接入。")
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.persist()

    def install(self):
        self.task_title.setText("03  /  准备运行环境")
        self.begin_operation(lambda j: runtime.install_runtime(j.task, j.log.emit, j.progress.emit),
                             lambda result: self.task_detail.setText("Ollama 运行环境已就绪，可以一键部署模型。"))

    def build_chat(self):
        box = self.page("PRIVATE CONVERSATIONS", "对话，从本机开始", "直接连接本地模型，逐字显示回复。对话仅保存在本次窗口的内存中。")
        row = QHBoxLayout()
        row.addWidget(label("当前模型", "muted"))
        self.chat_model = label("检查中…", "section")
        row.addWidget(self.chat_model, 1)
        row.addWidget(button("选择模型", lambda: self.navigate(1)))
        self.clear_button = button("清空对话", self.clear_chat)
        row.addWidget(self.clear_button)
        box.addLayout(row)
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setMinimumHeight(365)
        self.transcript.setProperty("_i18n_plain_ui", True)
        self.transcript.setPlainText("你好！部署或选择一个本地模型，然后发送第一条消息。")
        box.addWidget(self.transcript, 1)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("输入消息…（上下文按所选部署方案配置）")
        self.prompt.setMaximumHeight(100)
        box.addWidget(self.prompt)
        row = QHBoxLayout()
        self.reply_language = QComboBox()
        for title, value in [("跟随用户输入", "auto"), ("简体中文", "zh_CN"), ("English", "en")]:
            self.reply_language.addItem(title, value)
        self.reply_language.setCurrentIndex(max(0,self.reply_language.findData(self.settings.get("response_language","auto"))))
        self.reply_language.currentIndexChanged.connect(self.save_reply_language)
        row.addWidget(self.reply_language)
        self.chat_status = label("本地推理 · 不需要云端密钥", "muted")
        row.addWidget(self.chat_status, 1)
        self.stop_chat_button = button("停止生成", self.stop_chat)
        self.stop_chat_button.setEnabled(False)
        row.addWidget(self.stop_chat_button)
        self.send_button = button("发送消息  ↑", self.send_chat, True)
        row.addWidget(self.send_button)
        box.addLayout(row)

    def clear_chat(self):
        if self.chat_job:
            return
        self.messages = []
        self.answer = ""
        self.transcript.clear()

    def render_chat(self):
        self.transcript.setProperty("_i18n_plain_ui", False)
        text = "\n\n".join((tr("你") if m["role"] == "user" else tr("助手")) + "\n" + m["content"] for m in self.messages)
        if self.chat_job:
            text += "\n\n" + tr("助手") + "\n" + self.answer
        self.transcript.setPlainText(text)
        bar = self.transcript.verticalScrollBar()
        bar.setValue(bar.maximum())

    def send_chat(self):
        text = self.prompt.toPlainText().strip()
        if not text or self.chat_job:
            return
        if self.operation:
            self.error("部署任务正在进行，请完成或取消后再开始对话。")
            return
        if not self.active_model:
            self.error("请先部署或选择一个已安装模型。")
            return
        self.messages.append({"role": "user", "content": text})
        self.prompt.clear()
        self.answer = ""
        self.send_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.local_combo.setEnabled(False)
        self.stop_chat_button.setEnabled(True)
        self.chat_status.setText("正在本机生成…首次加载可能较慢")
        snapshot = [dict(m) for m in self.messages[-20:]]
        self.chat_job = self.launch(lambda j: runtime.stream_chat(self.active_model, snapshot, j.task, j.token.emit, self.settings.get("response_language","auto"), self.settings.get("model_plans",{}).get(self.active_model,{}).get("context",4096)),
                                    self.chat_complete, self.chat_failed)
        self.chat_job.token.connect(self.receive_token)
        self.chat_job.finished.connect(self.chat_finished)
        self.render_chat()

    def receive_token(self, token):
        self.answer += token
        self.render_chat()

    def chat_complete(self, answer):
        self.answer = answer
        self.messages.append({"role": "assistant", "content": answer})
        self.chat_status.setText("生成完成 · 本地推理")

    def chat_failed(self, message):
        if self.answer:
            self.messages.append({"role": "assistant", "content": self.answer + "\n[生成中断]"})
        else:
            # An unanswered user turn must not pollute the next request's history.
            failed = self.messages.pop()
            self.prompt.setPlainText(failed["content"])
        self.chat_status.setText(message)
        self.log(message)

    def chat_finished(self):
        self.chat_job = None
        self.send_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.local_combo.setEnabled(True)
        self.stop_chat_button.setEnabled(False)
        self.render_chat()

    def stop_chat(self):
        if self.chat_job:
            self.chat_job.task.cancel()
            self.stop_chat_button.setEnabled(False)
            self.chat_status.setText("正在停止…")

    def build_api(self):
        box = self.page("BUILD WITH LOCAL AI", "把模型接入你的应用", "部署后，Ollama 同时提供原生 API 和 OpenAI 兼容的聊天接口。")
        frame, col = card()
        row = QHBoxLayout()
        row.addWidget(label("本地服务地址", "muted"))
        row.addStretch()
        row.addWidget(label("LOOPBACK", "badge"))
        col.addLayout(row)
        self.endpoint = label(runtime.BASE_URL + "/v1", "metric")
        self.endpoint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(self.endpoint)
        self.api_model = label("", "muted")
        col.addWidget(self.api_model)
        col.addWidget(label("本软件启动的服务仅绑定 127.0.0.1。复用已有 Ollama 时，监听范围沿用该服务的配置。", "muted", True))
        col.addWidget(label("本机 Ollama 不校验 API Key；示例中的 ollama 只是 SDK 所需的占位值。", "muted", True))
        box.addWidget(frame)
        self.code_tabs = QTabWidget()
        self.code_editors = []
        for title in ["Python · OpenAI SDK", "PowerShell", "cURL · macOS / Linux"]:
            pane = QWidget()
            col = QVBoxLayout(pane)
            editor = QPlainTextEdit()
            editor.setObjectName("code")
            editor.setReadOnly(True)
            editor.setMinimumHeight(280)
            col.addWidget(editor)
            col.addWidget(button("复制调用示例", lambda checked=False, e=editor: QApplication.clipboard().setText(e.toPlainText())),
                          alignment=Qt.AlignmentFlag.AlignRight)
            self.code_editors.append(editor)
            self.code_tabs.addTab(pane, title)
        box.addWidget(self.code_tabs)
        self.test_api_button = button("验证 API 调用", self.test_api, True)
        box.addWidget(self.test_api_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.api_result = QPlainTextEdit()
        self.api_result.setReadOnly(True)
        self.api_result.setPlaceholderText("点击验证，发送一条真实的 OpenAI 兼容 API 请求。")
        self.api_result.setMinimumHeight(130)
        box.addWidget(self.api_result)
        box.addStretch()

    def update_api(self):
        tag = self.active_model or "qwen3:1.7b"
        self.api_model.setText("模型：" + (self.active_model or "请先部署模型（以下为示例）"))
        py = ('# pip install openai\nfrom openai import OpenAI\n\n'
              f'client = OpenAI(base_url="{runtime.BASE_URL}/v1", api_key="ollama")\n'
              'response = client.chat.completions.create(\n'
              f'    model={json.dumps(tag)},\n'
              '    messages=[{"role": "user", "content": "你好，请介绍一下自己"}],\n'
              '    reasoning_effort="none",\n'
              '    max_tokens=256,\n)\nprint(response.choices[0].message.content)')
        body = json.dumps({"model": tag, "messages": [{"role": "user", "content": "你好"}], "stream": False}, ensure_ascii=False, indent=2)
        ps = (f"$body = @'\n{body}\n'@\nInvoke-RestMethod -Method Post `\n"
              f"  -Uri '{runtime.BASE_URL}/api/chat' `\n"
              "  -ContentType 'application/json; charset=utf-8' `\n"
              "  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))")
        curl = f"curl {runtime.BASE_URL}/api/chat \\\n  -H 'Content-Type: application/json' \\\n  -d '{body}'"
        for editor, content in zip(self.code_editors, [py, ps, curl]):
            editor.setPlainText(content)

    def test_api(self):
        if not self.active_model:
            self.error("请先部署或选择模型。")
            return
        self.test_api_button.setEnabled(False)
        self.api_result.setPlainText("正在发送请求…首次加载可能需要较长时间。")
        body = {"model": self.active_model, "messages": [{"role": "user", "content": "Reply with OK."}],
                "max_tokens": 64, "stream": False, "reasoning_effort": "none"}
        def complete(result):
            self.api_result.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        def failed(message):
            self.api_result.setPlainText(tr(message))
            self.log(message)
        job = self.launch(lambda j: runtime.request("/v1/chat/completions", body, 180, j.task), complete, failed)
        job.finished.connect(lambda: self.test_api_button.setEnabled(True))

    def build_logs(self):
        box = self.page("RUNTIME DIAGNOSTICS", "每一步，都有迹可循", "查看真实命令行输出、下载状态和错误信息。日志保存在当前用户的本地目录。")
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("code")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setMinimumHeight(430)
        box.addWidget(self.log_view, 1)
        box.addWidget(label(str(DATA_DIR), "muted", True))
        box.addWidget(button("复制日志", lambda: QApplication.clipboard().setText(self.log_view.toPlainText())),
                      alignment=Qt.AlignmentFlag.AlignLeft)
        box.addWidget(label("关闭窗口会取消本软件正在进行的任务。已启动的 Ollama 服务继续运行，外部应用仍可调用 API。", "muted", True))

    def closeEvent(self, event):
        self.timer.stop()
        for job in list(self.jobs):
            job.task.cancel()
        event.accept()
