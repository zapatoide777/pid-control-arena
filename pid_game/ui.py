"""Control Arena: reproducción independiente de la evaluación física."""
import math
from pathlib import Path
import sys
import time
from PySide6.QtCore import Qt, QTimer, QElapsedTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup, QPauseAnimation
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QBrush, QLinearGradient, QFont, QPen
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QDoubleSpinBox, QSlider, QStackedWidget,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QScrollArea, QComboBox, QAbstractSpinBox, QGraphicsOpacityEffect,
)
from PySide6.QtCharts import QChart, QChartView, QValueAxis, QBarSeries, QBarSet, QBarCategoryAxis, QStackedBarSeries
from .controller import Gains, DEMO_GAINS
from .game import Game, State, Phase
from .simulation import simulate, hint, DURATION, STABILITY_WINDOW, STABLE_FROM, DT, STEP_TIME, STEP_DEGREES, iae_segment
from .storage import Ranking
from .motion import ArcadeButton, ReportSweep
from . import motion
from .theme import (BG, PLOT, SURFACE, SURFACE_RAISED, LINE, GRID, TEXT, MUTED as THEME_MUTED,
                    CYAN, BLUE, LIME, FONT_BODY, FONT_DISPLAY, FONT_DATA, FONT_FILES)
from .visuals import PendulumView, ResponseChart, AttemptStrip, AnalysisTrace, GainReadout, prepare_chart, GREEN, MUTED
from .guide_view import EducationalGuidePage

PRE_ROLL = .65  # preparación visual, fuera del IAE
STYLE = """
QWidget { font-family: '__BODY__'; font-size: 13px; color: #ecf5fa; }
QMainWindow, QWidget#root { background: #0a1728; }
QFrame#card { background: transparent; border: none; }
QFrame#instrumentPanel { background: #0c1c2e; border: 1px solid #1a334b; border-radius: 8px; }
QFrame#dockPanel { background: #0c1c2e; border: 1px solid #1a334b; border-radius: 8px; }
QFrame#modalCard { background: #102238; border: 1px solid #23435f; border-radius: 12px; }
QFrame#modalInner { background: transparent; border: none; }
QLabel { background: transparent; }
QLabel#brand { font-family: '__BODY__'; color: #a7e35c; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; }
QLabel#title { font-family: '__DISPLAY__'; font-size: 26px; font-weight: 700; letter-spacing: 1.5px; }
QLabel#hero { font-family: '__DISPLAY__'; font-size: 50px; font-weight: 700; }
QLabel#heading { font-family: '__DISPLAY__'; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }
QLabel#muted { font-family: '__BODY__'; color: #8faec4; font-size: 12px; }
QLabel#metric { font-family: '__DATA__'; font-size: 24px; font-weight: 600; color: #5dd8f0; }
QLabel#telemetry { font-family: '__DATA__'; font-size: 21px; font-weight: 600; color: #5dd8f0; }
QLabel#telemetrySmall { font-family: '__DATA__'; font-size: 15px; font-weight: 600; color: #5dd8f0; }
QLabel#score { font-family: '__DATA__'; font-size: 64px; font-weight: 700; color: #a7e35c; }
QPushButton { background: #a7e35c; color: #0b1e17; border: 1px solid #94d84a; border-radius: 6px; padding: 10px 20px; min-height: 24px; font-weight: 700; font-family: '__BODY__'; font-size: 13px; outline: none; }
QPushButton:hover { background: #bbf46d; border-color: #a7ea55; color: #05140d; }
QPushButton:pressed { background: #90d143; border-color: #7ebf32; }
QPushButton:focus { outline: none; }
QPushButton:disabled { background: #142536; color: #4b667a; border: 1px solid #1c354a; }
QPushButton#secondary { background: #13273c; color: #e2eef6; border: 1px solid #274563; font-weight: 600; }
QPushButton#secondary:hover { background: #1b3753; border-color: #3d6c96; color: #ffffff; }
QPushButton#secondary:pressed { background: #0e1e30; border-color: #1e354e; }
QPushButton#secondary:focus { outline: none; }
QPushButton#secondary:disabled { background: #0d1a27; color: #3b5366; border-color: #17293a; }
QComboBox:focus, QSlider:focus { border: 1px solid #5dd8f0; }
QLineEdit, QComboBox { background: #0c1a2a; border: 1px solid #1e374f; border-radius: 4px; padding: 7px; min-height: 24px; color: #edf7fc; selection-background-color: #267ea2; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #5dd8f0; }
QDoubleSpinBox { background: #0c1a2a; border: 1px solid #1e374f; border-radius: 6px; padding: 4px; min-height: 28px; color: #edf7fc; font-family: '__DATA__'; font-size: 21px; selection-background-color: #267ea2; }
QDoubleSpinBox:focus { border: 1px solid #5dd8f0; }
QDoubleSpinBox QLineEdit { padding: 0 4px; border: none; background: transparent; min-height: 0; font-size: 21px; }
QDoubleSpinBox:disabled, QDoubleSpinBox QLineEdit:disabled { color: #6a8292; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { background: #162c3f; border: none; width: 20px; border-radius: 3px; }
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #234563; }
QComboBox QAbstractItemView { background: #102238; color: #edf7fc; selection-background-color: #326eab; }
QSlider::groove:horizontal { height: 4px; background: #1a3246; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #3d90d5; border-radius: 2px; }
QSlider::handle:horizontal { background: #a7e35c; border: 2px solid #0a1728; width: 16px; margin: -6px 0; border-radius: 8px; }
QSlider::handle:horizontal:hover { background: #c7f182; }
QProgressBar { background: #162b3d; border: none; border-radius: 3px; min-height: 6px; max-height: 6px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5dd8f0, stop:1 #a7e35c); border-radius: 3px; }
QTableWidget { background: #0c1a2c; color: #edf7fc; border: 1px solid #1a334b; border-radius: 6px; gridline-color: #1a334b; alternate-background-color: #102338; selection-background-color: #234d6e; }
QHeaderView::section { background: #162c40; color: #d5e8ef; border: none; padding: 10px 6px; font-weight: 600; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical { background: #112334; width: 10px; margin: 0; border-radius: 5px; }
QScrollBar::handle:vertical { background: #406782; min-height: 32px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #5dd8f0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


def configure_app(app):
    font_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    for name in FONT_FILES:
        path = font_dir / name
        if path.is_file():
            QFontDatabase.addApplicationFont(str(path))
    available = set(QFontDatabase.families())
    body = FONT_BODY if FONT_BODY in available else "Segoe UI"
    display = FONT_DISPLAY if FONT_DISPLAY in available else body
    data = FONT_DATA if FONT_DATA in available else "Consolas"
    style = STYLE.replace("__BODY__", body).replace("__DISPLAY__", display).replace("__DATA__", data)
    for old, new in (("#0a1728", BG), ("#12243a", PLOT), ("#102238", SURFACE),
                     ("#1a3046", SURFACE_RAISED), ("#45677a", LINE), ("#30475b", GRID),
                     ("#edf7fc", TEXT), ("#a9bfce", THEME_MUTED), ("#6adcf1", CYAN),
                     ("#326eab", BLUE), ("#a7e35c", LIME)):
        style = style.replace(old, new)
    app.setStyle("Fusion")
    app.setStyleSheet(style)


def label(text, kind="", wrap=False):
    widget = QLabel(text)
    widget.setObjectName(kind)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def card():
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 18, 22, 18)
    layout.setSpacing(12)
    return frame, layout


def button(text, callback, secondary=False):
    widget = ArcadeButton(text)
    if secondary:
        widget.setObjectName("secondary")
    widget.clicked.connect(callback)
    return widget


class GainControl(QWidget):
    def __init__(self, name, meaning, unit, maximum, value):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        row = QHBoxLayout()
        row.addWidget(label(f"{name}  ·  {meaning}", "brand"))
        row.addStretch()
        self.spin = QDoubleSpinBox()
        self.spin.setRange(0, maximum)
        self.spin.setDecimals(2)
        self.spin.setSingleStep(.01)
        self.spin.setKeyboardTracking(False)
        self.spin.setFixedSize(140, 52)
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setAccessibleName(f"{name}, {meaning}")
        self.spin.setAccessibleDescription(f"Valor entre 0 y {maximum}; unidad {unit}")
        row.addWidget(self.spin)
        layout.addLayout(row)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, maximum*100)
        self.slider.setMinimumHeight(25)
        self.slider.setAccessibleName(f"Ajustar {name}, {meaning}")
        self.slider.valueChanged.connect(lambda v: self.spin.setValue(v/100))
        self.spin.valueChanged.connect(lambda v: self.slider.setValue(round(v*100)))
        self.spin.setValue(value)
        layout.addWidget(self.slider)
        layout.addWidget(label(unit, "muted"))


class ReportOverlayPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.backdrop = None

    def set_backdrop(self, pixmap):
        self.backdrop = pixmap
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.backdrop and not self.backdrop.isNull():
            p.drawPixmap(self.rect(), self.backdrop)
        else:
            p.fillRect(self.rect(), QColor(BG))
        p.fillRect(self.rect(), QColor(10, 23, 40, 218))


class MainWindow(QMainWindow):
    def __init__(self, data_path=None):
        super().__init__()
        self.setWindowTitle("PID / Control Arena")
        self.resize(1400, 940)
        self.setMinimumSize(1120, 800)
        self.game = Game()
        self.ranking = Ranking(data_path or Path(__file__).resolve().parent.parent / "data/ranking.json")
        self.active_result = None
        self.playback_clock = QElapsedTimer()
        self.playback_active = False
        self.playback_rate = 1.0
        self.paused_at = None
        self.pause_total_ms = 0
        self.report_ready_at = 0.0
        self.cumulative_iae = []
        self.current_ranking_row = None
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 12, 18, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("PID  /  EQUILIBRIO", "title"))
        header.addLayout(titles)
        header.addStretch()
        layout.addLayout(header)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self._build_waiting()
        self._build_playing()
        self._build_finished()
        self._build_report()
        self._build_guide()
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def _build_waiting(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        hero, body = card()
        row = QHBoxLayout()
        copy = QVBoxLayout()
        copy.addStretch()
        copy.addWidget(label("Controla el\npéndulo", "hero"))
        copy.addWidget(label("Ajusta Kp, Ki y Kd para seguir la referencia.", "muted", True))
        copy.addSpacing(18)
        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("Tu nombre")
        self.alias_edit.setAccessibleName("Nombre o alias del jugador")
        self.alias_edit.setMaxLength(32)
        self.alias_edit.setMaximumWidth(440)
        copy.addWidget(self.alias_edit)
        self.start_button = button("Jugar  →", self.start_game)
        self.start_button.setMaximumWidth(440)
        copy.addWidget(self.start_button)
        guide_row_container = QWidget()
        guide_row_container.setMaximumWidth(440)
        guide_row_layout = QHBoxLayout(guide_row_container)
        guide_row_layout.setContentsMargins(0, 4, 0, 0)
        guide_row_layout.setSpacing(10)
        self.iae_button = button("¿Qué es el IAE?", lambda: self.open_guide("iae"), secondary=True)
        self.pid_guide_button = button("¿Qué hacen Kp, Ki y Kd?", lambda: self.open_guide("kp"), secondary=True)
        guide_row_layout.addWidget(self.iae_button)
        guide_row_layout.addWidget(self.pid_guide_button)
        copy.addWidget(guide_row_container)
        copy.addSpacing(6)
        copy.addWidget(label("Solo el tercer intento entra al ranking.", "muted", True))
        copy.addStretch()
        row.addLayout(copy, 5)
        scene = PendulumView()
        scene.angle = .23
        row.addWidget(scene, 5)
        body.addLayout(row)
        outer.addWidget(hero, 1)
        self.start_warning = label(self.ranking.warning, "muted", True)
        outer.addWidget(self.start_warning)
        self.stack.addWidget(page)

    def _build_playing(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        top = QHBoxLayout()
        headings = QVBoxLayout()
        self.attempt_label = label("DEMOSTRACIÓN", "heading")
        self.phase_label = label("", "muted")
        headings.addWidget(self.attempt_label)
        headings.addWidget(self.phase_label)
        top.addLayout(headings, 2)
        self.attempt_strip = AttemptStrip()
        top.addWidget(self.attempt_strip, 3)
        outer.addLayout(top)
        workspace = QHBoxLayout()
        workspace.setSpacing(14)
        self.response_chart = ResponseChart()
        workspace.addWidget(self.response_chart, 8)
        instrument, content = card()
        content.setContentsMargins(12, 10, 12, 10)
        instrument.setMinimumWidth(285)
        instrument.setObjectName("instrumentPanel")
        self.pendulum = PendulumView(length_scale=1.4)
        content.addWidget(self.pendulum, 1)
        telemetry = QHBoxLayout()
        telemetry.setSpacing(16)
        self.angle_label = label("0.0°", "telemetry")
        self.time_label = label("0.00 s", "telemetry")
        self.error_label = label("0.00 pts", "telemetrySmall")
        self.angle_caption = label("Ángulo", "muted")
        self.time_caption = label(f"Tiempo / {DURATION:g} s", "muted")
        for caption, metric in ((self.angle_caption, self.angle_label),
                                (self.time_caption, self.time_label)):
            col = QVBoxLayout()
            col.addWidget(caption)
            col.addWidget(metric)
            telemetry.addLayout(col, 1)
        content.addLayout(telemetry)
        iae_row = QHBoxLayout()
        iae_row.addWidget(label("PUNTAJE (IAE)", "muted"))
        iae_row.addWidget(self.error_label)
        iae_row.addStretch()
        content.addLayout(iae_row)
        self.fall_label = label("PREPARANDO EMPUJÓN", "muted", True)
        content.addWidget(self.fall_label)
        workspace.addWidget(instrument, 3)
        outer.addLayout(workspace, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, round(DURATION*1000))
        self.progress.setTextVisible(False)
        outer.addWidget(self.progress)
        dock, content = card()
        dock.setObjectName("dockPanel")
        content.setContentsMargins(16, 12, 16, 12)
        row = QHBoxLayout()
        self.gain_controls = [GainControl("Kp", "corrección", "N·m/rad", 10, DEMO_GAINS.kp),
                              GainControl("Ki", "acumulación", "N·m/(rad·s)", 5, DEMO_GAINS.ki),
                              GainControl("Kd", "amortiguación", "N·m·s/rad", 3, DEMO_GAINS.kd)]
        for control in self.gain_controls:
            row.addWidget(control, 1)
        content.addLayout(row)
        outer.addWidget(dock)
        actions = QHBoxLayout()
        self.edit_note = label("", "muted", True)
        actions.addWidget(self.edit_note, 1)
        self.speed_combo = QComboBox()
        for caption, rate in (("1× · tiempo real", 1.0), ("0,5× · cámara lenta", .5)):
            self.speed_combo.addItem(caption, rate)
        self.speed_combo.setAccessibleName("Velocidad de reproducción")
        actions.addWidget(self.speed_combo)
        self.pause_button = button("Pausar", self.toggle_pause, True)
        actions.addWidget(self.pause_button)
        self.skip_button = button("Omitir demo", self.skip_demo, True)
        actions.addWidget(self.skip_button)
        self.run_button = button("Ejecutar intento 1  →", self.run_trial)
        actions.addWidget(self.run_button)
        outer.addLayout(actions)
        self.stack.addWidget(page)

    def _build_report(self):
        self.report_page = ReportOverlayPage()
        outer = QVBoxLayout(self.report_page)
        outer.setContentsMargins(40, 16, 40, 16)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.modal_card = QFrame()
        self.modal_card.setObjectName("modalCard")
        self.modal_card.setMaximumWidth(880)
        modal_layout = QVBoxLayout(self.modal_card)
        modal_layout.setContentsMargins(28, 22, 28, 20)
        modal_layout.setSpacing(14)
        outer.addWidget(self.modal_card)

        self.report_title = label("ANÁLISIS DEL INTENTO", "heading")
        modal_layout.addWidget(self.report_title)
        self.report_strip = AttemptStrip()
        modal_layout.addWidget(self.report_strip)
        self.report_sweep = ReportSweep()
        modal_layout.addWidget(self.report_sweep)

        middle = QHBoxLayout()
        middle.setSpacing(20)

        score = QFrame()
        score.setObjectName("modalInner")
        score_layout = QVBoxLayout(score)
        score_layout.setContentsMargins(18, 14, 18, 14)
        score_layout.setSpacing(6)
        score_layout.addWidget(label("PUNTAJE DE ERROR  /  IAE", "brand"))
        self.report_iae = label("", "score")
        score_layout.addWidget(self.report_iae)
        score_layout.addWidget(label("Puntaje de error  ·  (Menor puntaje = mejor control)", "muted"))
        self.report_delta = label("", "heading", True)
        score_layout.addWidget(self.report_delta)
        self.report_status = label("", "muted", True)
        score_layout.addWidget(self.report_status)
        self.report_trace = AnalysisTrace()
        score_layout.addWidget(self.report_trace, 1)
        middle.addWidget(score, 5)

        guidance = QFrame()
        guidance.setObjectName("modalInner")
        guide_layout = QVBoxLayout(guidance)
        guide_layout.setContentsMargins(18, 14, 18, 14)
        guide_layout.setSpacing(8)
        guide_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.guide_title = label("TU SIGUIENTE MOVIMIENTO", "brand")
        guide_layout.addWidget(self.guide_title)
        self.feedback_label = label("", wrap=True)
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.feedback_label.setStyleSheet("font-size: 16px; font-weight: 500; color: #ecf5fa; min-height: 42px;")
        guide_layout.addWidget(self.feedback_label)
        guide_layout.addSpacing(14)
        self.report_gains = GainReadout()
        guide_layout.addWidget(self.report_gains)
        guide_layout.addStretch(1)
        middle.addWidget(guidance, 5)

        modal_layout.addLayout(middle, 1)

        self.report_score_effect = QGraphicsOpacityEffect(score)
        self.report_hint_effect = QGraphicsOpacityEffect(self.feedback_label)
        score.setGraphicsEffect(self.report_score_effect)
        self.feedback_label.setGraphicsEffect(self.report_hint_effect)
        self.report_animation = QParallelAnimationGroup(self)
        motion.on_motion_change(self._report_motion_changed)
        score_fade = QPropertyAnimation(self.report_score_effect, b"opacity")
        score_fade.setDuration(480)
        score_fade.setStartValue(.18)
        score_fade.setEndValue(1.0)
        score_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.report_animation.addAnimation(score_fade)
        hint_sequence = QSequentialAnimationGroup()
        hint_sequence.addAnimation(QPauseAnimation(190))
        hint_fade = QPropertyAnimation(self.report_hint_effect, b"opacity")
        hint_fade.setDuration(550)
        hint_fade.setStartValue(.12)
        hint_fade.setEndValue(1.0)
        hint_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        hint_sequence.addAnimation(hint_fade)
        self.report_animation.addAnimation(hint_sequence)

        self.analysis_progress = QProgressBar()
        self.analysis_progress.setRange(0, 3000)
        self.analysis_progress.setTextVisible(False)
        modal_layout.addWidget(self.analysis_progress)

        actions = QHBoxLayout()
        self.analysis_label = label("", "muted")
        actions.addWidget(self.analysis_label, 1)
        self.continue_button = button("CONTINUAR  →", self.continue_trial)
        actions.addWidget(self.continue_button)
        modal_layout.addLayout(actions)

        self.stack.addWidget(self.report_page)

    def _build_finished(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        summary, content = card()
        self.final_title = label("", "heading", True)
        self.final_metric = label("", "metric", True)
        self.final_detail = label("", "muted", True)
        for widget in (self.final_title, self.final_metric, self.final_detail):
            content.addWidget(widget)
        outer.addWidget(summary)
        middle = QHBoxLayout()
        rank_frame, content = card()
        content.addWidget(label("CLASIFICACIÓN / TOP 10", "heading"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["#", "Piloto", "Puntaje (IAE)", "Kp / Ki / Kd", "Estado", "Fecha"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        content.addWidget(self.table)
        middle.addWidget(rank_frame, 3)
        self.ranking_chart = QChartView(QChart())
        self.ranking_chart.setBackgroundBrush(QColor("#12243a"))
        self.ranking_chart.setFrameShape(QFrame.Shape.NoFrame)
        self.ranking_chart.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.ranking_chart.setStyleSheet("border: 1px solid #1a334b; border-radius: 6px; background: #12243a;")
        self.ranking_chart.setMinimumWidth(300)
        middle.addWidget(self.ranking_chart, 2)
        outer.addLayout(middle, 1)
        self.save_warning = label("", "muted", True)
        outer.addWidget(self.save_warning)
        actions = QHBoxLayout()
        actions.addStretch()
        self.new_button = button("Nueva partida", self.new_game)
        actions.addWidget(self.new_button)
        actions.addWidget(button("SALIR", self.close, True))
        outer.addLayout(actions)
        self.stack.addWidget(page)

    def start_game(self):
        self.game.begin(self.alias_edit.text())
        self.stack.setCurrentIndex(1)
        for control, value in zip(self.gain_controls, (DEMO_GAINS.kp, DEMO_GAINS.ki, DEMO_GAINS.kd)):
            control.spin.setValue(value)
        self.attempt_strip.results, self.attempt_strip.active = [], -1
        self.attempt_strip.playing = True
        self.attempt_strip.update()
        self.attempt_label.setText("Demostración")
        self.phase_label.setText("PID inicial · sin gastar intentos")
        self.edit_note.setText("Observa la respuesta al impulso.")
        self._set_editing(False)
        self.skip_button.setVisible(self.game.demo_seen)
        self._start_playback(simulate(DEMO_GAINS))

    def _set_editing(self, editing):
        for control in self.gain_controls:
            control.setEnabled(editing)
        self.run_button.setEnabled(editing)
        self.speed_combo.setEnabled(editing)

    def _start_playback(self, result):
        self.active_result = result
        self.playback_rate = self.speed_combo.currentData()
        self.paused_at, self.pause_total_ms = None, 0
        self.pause_button.setEnabled(True)
        self.pause_button.setText("Pausar")
        self.cumulative_iae = [0.0]
        for a, b in zip(result.samples, result.samples[1:]):
            self.cumulative_iae.append(self.cumulative_iae[-1] +
                iae_segment(a, b))
        self.response_chart.clear()
        self.playback_active = True
        self.playback_clock.start()
        self._render_sample(0, preparing=True)

    def toggle_pause(self):
        if not self.playback_active:
            return
        if self.paused_at is None:
            self.paused_at = self.playback_clock.elapsed()
            self.pause_button.setText("Reanudar")
        else:
            self.pause_total_ms += self.playback_clock.elapsed()-self.paused_at
            self.paused_at = None
            self.pause_button.setText("Pausar")

    def skip_demo(self):
        self.game.complete_demo(skipped=True)
        self.playback_active = False
        self.attempt_strip.playing = False
        self._show_editing("Elige tus ganancias.")

    def _show_editing(self, message):
        self.stack.setCurrentIndex(1)
        number = len(self.game.attempts)+1
        self.attempt_label.setText("Ajusta el controlador")
        self.phase_label.setText(f"Intento {number} de 3")
        self.run_button.setText(f"Ejecutar intento {number}  →")
        self._set_editing(True)
        self.pause_button.setEnabled(False)
        self.skip_button.hide()
        self.edit_note.setText(message)
        self.attempt_strip.results = list(self.game.attempts)
        self.attempt_strip.active = len(self.game.attempts)
        self.attempt_strip.playing = False
        self.attempt_strip.update()

    def run_trial(self):
        for control in self.gain_controls:
            control.spin.interpretText()
        result = self.game.launch(Gains(*(c.spin.value() for c in self.gain_controls)))
        self._set_editing(False)
        self.attempt_strip.playing = True
        self.attempt_strip.update()
        self.attempt_label.setText("EN MARCHA")
        self.phase_label.setText(f"{DURATION:g} s físicos · reproducción a {self.speed_combo.currentData():g}×")
        self.edit_note.setText(f"Referencia: 0° → {STEP_DEGREES:g}° a los {STEP_TIME:g} s  ·  Margen de estabilidad: ±5°")
        self._start_playback(result)

    def _render_sample(self, index, preparing=False):
        result = self.active_result
        if result is None:
            return
        sample = result.samples[index]
        self.pendulum.angle = sample.angle
        self.pendulum.reference_angle = sample.reference
        self.pendulum.fallen = any(abs(s.angle) >= math.pi/2 for s in result.samples[:index+1])
        self.pendulum.sample_time = -1 if preparing else sample.time
        self.pendulum.trail = [s.angle for s in result.samples[max(0, index-250):index+1:12]]
        self.pendulum.update()
        self.angle_label.setText(f"{math.degrees(sample.angle):.1f}°")
        self.time_label.setText(f"{sample.time:.2f} s")
        self.error_label.setText(f"{self.cumulative_iae[index]:.2f} pts")
        for metric in (self.angle_label, self.time_label, self.error_label):
            metric.setMinimumWidth(metric.fontMetrics().horizontalAdvance(metric.text()) + 2)
        self.fall_label.setText("Preparando…" if preparing else
            ("Caída registrada" if self.pendulum.fallen else
             ("Empujón inicial · 2 rad/s" if sample.time < .2 else
              "Margen de estabilidad: ±5°")))
        self.progress.setValue(round(sample.time*1000))
        self.response_chart.reveal(result, index)

    def tick(self):
        if self.playback_active and self.active_result is not None and self.paused_at is None:
            elapsed = (self.playback_clock.elapsed()-self.pause_total_ms)/1000
            index = min(round(DURATION*1000), max(0, int(((elapsed-PRE_ROLL)*self.playback_rate + 1e-12)/DT)))
            self._render_sample(index, preparing=elapsed < PRE_ROLL)
            if index == round(DURATION*1000):
                self._complete_playback()
        if self.stack.currentIndex() == 3:
            remaining = max(0, self.report_ready_at-time.monotonic())
            self.continue_button.setEnabled(remaining <= 0)
            self.analysis_progress.setValue(round(3000-min(3, remaining)*1000))
            self.analysis_label.setText(f"Preparando  ·  {math.ceil(remaining)} s" if remaining else
                                        "Listo para continuar")
            self.continue_button.setText("Ver ranking  →" if self.game.state is State.FINISHED else "Siguiente intento  →")

    def _complete_playback(self):
        self.playback_active = False
        self.attempt_strip.playing = False
        self.attempt_strip.update()
        self.pause_button.setEnabled(False)
        if self.game.phase is Phase.DEMO:
            self.game.complete_demo()
            self._show_editing("Tu turno: ajusta Kp, Ki y Kd.")
            return
        self.game.finish_playback(time.monotonic())
        if self.game.state is State.FINISHED:
            self.ranking.add_game(self.game)
        self.show_report()

    def _report_motion_changed(self, preference):
        if preference == Qt.MotionPreference.ReducedMotion:
            self.report_animation.stop()
            self.report_score_effect.setOpacity(1.0)
            self.report_hint_effect.setOpacity(1.0)

    def show_report(self):
        result = self.game.attempts[-1]
        number = len(self.game.attempts)
        self.report_title.setText(f"INTENTO {number:02d}  /  {'ESTABLE' if result.success else 'SIN EQUILIBRIO'}")
        self.report_iae.setText(f"{result.iae:.2f}")
        self.report_trace.result = result
        self.report_trace.update()
        self.report_gains.gains = result.gains
        self.report_gains.update()
        self.report_strip.results, self.report_strip.active = list(self.game.attempts), -1
        self.report_strip.update()
        self.report_strip.play()
        if number > 1:
            delta = self.game.attempts[-2].iae-result.iae
        else:
            delta = None
        if delta is None:
            comparison = "Primer registro"
        elif abs(delta) < .005:
            comparison = "Puntaje igual al intento anterior"
        else:
            comparison = f"{abs(delta):.2f} pts {'menos' if delta > 0 else 'más'} que el intento anterior"
        self.report_delta.setText(comparison)
        self.report_status.setText("Error dentro del margen de estabilidad: ±5° en ambas ventanas." if result.success else
            (f"Caída registrada a ±90° · análisis completo de {DURATION:g} s." if result.fallen else
             "Fuera del margen de estabilidad: ±5°."))
        self.guide_title.setText("LECTURA" if result.success else "PISTA")
        self.feedback_label.setText(("Buen control: error dentro del margen de estabilidad: ±5°."
            if number < 3 else "Estable. Este intento entra al ranking.")
            if result.success else hint(result))
        self.report_ready_at = max(time.monotonic()+3, self.game.ready_at)
        self.continue_button.setEnabled(False)
        self.report_page.set_backdrop(self.stack.widget(1).grab())
        self.stack.setCurrentIndex(3)
        self.report_animation.stop()
        if motion.reduced_motion():
            self.report_score_effect.setOpacity(1.0)
            self.report_hint_effect.setOpacity(1.0)
        else:
            self.report_score_effect.setOpacity(.18)
            self.report_hint_effect.setOpacity(.12)
            self.report_animation.start()
        self.report_sweep.play()
        self.tick()

    def continue_trial(self):
        if time.monotonic() < self.report_ready_at:
            return
        if self.game.state is State.FINISHED:
            self.show_results()
        else:
            self.game.continue_editing(time.monotonic())
            self._show_editing("Ajusta y vuelve a probar.")

    def show_results(self):
        current = self.ranking.add_game(self.game)
        ordered = self.ranking.ordered()
        rank = next(i+1 for i, r in enumerate(ordered) if r["id"] == current["id"])
        result = self.game.final
        self.final_title.setText(f"CLASIFICACIÓN / {self.game.alias}")
        self.final_metric.setText(f"{result.iae:.2f} pts   ·   puesto {rank} de {len(ordered)}")
        state = "Estabilización lograda" if result.success else ("Caída registrada" if result.fallen else "Fuera del criterio de estabilidad")
        self.final_detail.setText(f"Tercer intento · {state} · (Menor puntaje = mejor control)")
        self.save_warning.setText(self.ranking.warning)
        rows = ordered[:10] + ([current] if rank > 10 else [])
        self.table.setRowCount(len(rows))
        for row, record in enumerate(rows):
            actual = record["id"] == current["id"]
            gains = record["gains"]
            status = "Estable" if record["success"] else ("Caída" if record["fallen"] else "No estable")
            values = [str(ordered.index(record)+1), ("(actual) " if actual else "") + record["alias"],
                      f"{record['iae']:.2f}", f"{gains['kp']:.2f} / {gains['ki']:.2f} / {gains['kd']:.2f}", status, record["date"][:10]]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setToolTip(record["date"])
                if actual:
                    item.setBackground(QColor("#27483d"))
                    item.setForeground(QColor(GREEN))
                self.table.setItem(row, col, item)
            if actual:
                self.current_ranking_row = row
        self._draw_ranking(rows, ordered, current)
        self.stack.setCurrentIndex(2)
        QTimer.singleShot(0, self._reveal_current_ranking)

    def _reveal_current_ranking(self):
        if self.stack.currentIndex() == 2 and self.current_ranking_row is not None:
            self.table.scrollToItem(self.table.item(self.current_ranking_row, 1))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "stack"):
            QTimer.singleShot(0, self._reveal_current_ranking)

    def _draw_ranking(self, rows, ordered, current):
        chart = QChart()
        prepare_chart(chart)
        values = [r["iae"] for r in rows]
        positive = [value for value in values if value > 0]
        logarithmic = bool(positive) and max(values) > 30 * max(min(positive), .01)
        display_value = (lambda value: math.log10(1 + value)) if logarithmic else (lambda value: value)
        chart.setTitle("PUNTAJE DE ERROR · LOG₁₀" if logarithmic else "PUNTAJE DE ERROR")
        historical, actual = QBarSet("Histórico"), QBarSet("Actual")

        # Degradado azul/cyan tecnológico para barras históricas
        hist_grad = QLinearGradient(0, 1, 0, 0)
        hist_grad.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
        hist_grad.setColorAt(0.0, QColor("#163a5e"))
        hist_grad.setColorAt(0.7, QColor("#286ea8"))
        hist_grad.setColorAt(1.0, QColor("#4da6f5"))
        historical.setBrush(QBrush(hist_grad))
        historical.setPen(QPen(Qt.PenStyle.NoPen))

        # Degradado verde lima radiante para el intento actual del jugador
        act_grad = QLinearGradient(0, 1, 0, 0)
        act_grad.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
        act_grad.setColorAt(0.0, QColor("#2d6514"))
        act_grad.setColorAt(0.65, QColor("#72bf25"))
        act_grad.setColorAt(1.0, QColor("#b4f858"))
        actual.setBrush(QBrush(act_grad))
        actual.setPen(QPen(Qt.PenStyle.NoPen))

        categories = []
        for record in rows:
            categories.append(str(ordered.index(record)+1))
            is_current = record["id"] == current["id"]
            historical.append(0 if is_current else display_value(record["iae"]))
            actual.append(display_value(record["iae"]) if is_current else 0)

        series = QStackedBarSeries()
        count = len(categories)
        bar_width = 0.22 if count == 1 else (0.34 if count == 2 else (0.42 if count == 3 else 0.52))
        series.setBarWidth(bar_width)
        series.append(historical)
        series.append(actual)
        chart.addSeries(series)

        x, y = QBarCategoryAxis(), QValueAxis()
        x.append(categories)
        x.setTitleText("Puesto  ·  (verde = intento actual)")
        y.setRange(0, max(1, display_value(max(values))*1.18))
        y.setLabelFormat("%.1f")
        y.setTitleText("log₁₀(1 + IAE)" if logarithmic else "Puntaje de error")

        x.setLabelsFont(QFont(FONT_DATA, 10))
        x.setTitleFont(QFont(FONT_BODY, 9, QFont.Weight.Medium))
        x.setGridLineVisible(False)
        x.setLinePen(QPen(QColor("#243e54"), 1))

        y.setLabelsFont(QFont(FONT_DATA, 9))
        y.setTitleFont(QFont(FONT_BODY, 9, QFont.Weight.Medium))
        y.setGridLinePen(QPen(QColor(36, 62, 84, 160), 1, Qt.PenStyle.DashLine))
        y.setLinePen(QPen(QColor("#243e54"), 1))

        for axis, alignment in ((x, Qt.AlignmentFlag.AlignBottom), (y, Qt.AlignmentFlag.AlignLeft)):
            chart.addAxis(axis, alignment)
            axis.setLabelsColor(QColor(MUTED))
            axis.setTitleBrush(QColor(MUTED))
            series.attachAxis(axis)

        old = self.ranking_chart.chart()
        self.ranking_chart.setChart(chart)
        old.deleteLater()


    def _build_guide(self):
        self.guide_page = EducationalGuidePage(on_back=self.close_guide)
        self.stack.addWidget(self.guide_page)

    def open_guide(self, tab_id: str = "iae"):
        self.guide_return_index = self.stack.currentIndex()
        self.guide_page.select_tab(tab_id)
        self.stack.setCurrentIndex(4)

    def close_guide(self):
        self.stack.setCurrentIndex(getattr(self, "guide_return_index", 0))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showMaximized()
            else:
                self.showFullScreen()
            event.accept()
            return
        super().keyPressEvent(event)

    def new_game(self):
        self.game.reset()
        self.stack.setCurrentIndex(0)
        self.start_warning.setText(self.ranking.warning)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PID / Control Arena")
    configure_app(app)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
