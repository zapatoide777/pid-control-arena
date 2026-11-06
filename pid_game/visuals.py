"""Instrumentos dibujados y gráficas: presentación independiente del cálculo."""
import math
from PySide6.QtCore import Qt, QPointF, QRectF, QMargins, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF, QPainterPath, QLinearGradient, QRadialGradient, QFontMetrics
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QAreaSeries, QScatterSeries

from .motion import on_motion_change, reduced_motion
from .theme import (PLOT as NAVY, BLUE, LIME as GREEN, CYAN, TEXT, MUTED,
                    CORAL, GRID, LINE, FONT_BODY, FONT_DISPLAY, FONT_DATA)


def prepare_chart(chart):
    chart.setBackgroundBrush(QColor(NAVY))
    chart.setBackgroundRoundness(0)
    chart.setTitleBrush(QColor(TEXT))
    chart.setTitleFont(QFont(FONT_DISPLAY, 12, QFont.Weight.Bold))
    chart.legend().setVisible(False)
    chart.setMargins(QMargins(6, 6, 6, 6))


class AttemptStrip(QWidget):
    def __init__(self):
        super().__init__()
        self.results = []
        self.active = 0
        self.playing = False
        self._reveal = 1.0
        self.animation = QPropertyAnimation(self, b"reveal", self)
        self.animation.setDuration(650)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumHeight(68)
        on_motion_change(self._motion_changed)

    def _get_reveal(self):
        return self._reveal

    def _set_reveal(self, value):
        self._reveal = float(value)
        self.update()

    reveal = Property(float, _get_reveal, _set_reveal)

    def _motion_changed(self, preference):
        if preference == Qt.MotionPreference.ReducedMotion:
            self.animation.stop()
            self._set_reveal(1.0)

    def play(self):
        self.animation.stop()
        if reduced_motion():
            self._set_reveal(1.0)
            return
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap = 16
        width = max(1, (self.width() - 2 * gap) / 3)
        number_font = QFont(FONT_DISPLAY, 21, QFont.Weight.DemiBold)
        label_font = QFont(FONT_BODY, 9, QFont.Weight.DemiBold)
        value_font = QFont(FONT_DATA, 11)
        number_width = QFontMetrics(number_font).horizontalAdvance("03") + 12
        for i in range(3):
            x = i * (width + gap)
            done = i < len(self.results)
            current = i == self.active or (self.active < 0 and i == len(self.results) - 1)
            color = GREEN if done else (CYAN if current else MUTED)
            p.setPen(QPen(QColor(LINE), 1))
            p.drawLine(QPointF(x, 3), QPointF(x + width, 3))
            if done or current:
                p.setPen(QPen(QColor(color), 2))
                p.drawLine(QPointF(x, 3), QPointF(x + width * (self._reveal if current else 1), 3))
            p.setFont(number_font)
            p.setPen(QColor(color))
            p.drawText(QRectF(x, 10, number_width, 44), Qt.AlignmentFlag.AlignVCenter, f"0{i+1}")
            text_width = max(1, width - number_width)
            label = "RESULTADO" if done else (("EN JUEGO" if self.playing else "AJUSTANDO") if current else "PENDIENTE")
            value = f"{self.results[i].iae:.2f} pts" if done else ("Ajusta tu PID" if current else "—")
            for font, text, y, text_color in ((label_font, label, 12, color),
                                               (value_font, value, 33, TEXT if done or current else MUTED)):
                p.setFont(font)
                p.setPen(QColor(text_color))
                fitted = QFontMetrics(font).elidedText(text, Qt.TextElideMode.ElideRight, int(text_width))
                p.drawText(QRectF(x + number_width, y, text_width, 22), Qt.AlignmentFlag.AlignVCenter, fitted)



def pendulum_radius(width: int, height: int, length_scale: float = 1.0) -> float:
    """Longitud ilustrativa acotada al lienzo; el modelo físico no cambia."""
    base = max(30, min(width*.29, height*.29))
    fit = max(30, min((width-44)/2, height*.43-10))
    return min(fit, base*length_scale)


class PendulumView(QWidget):
    def __init__(self, length_scale=1.0):
        super().__init__()
        self.angle = 0.0
        self.reference_angle = 0.0
        self.sample_time = -1.0
        self.trail = []
        self.length_scale = length_scale
        self.setMinimumSize(200, 140)

    def paintEvent(self, event):
        from .scene3d import render_pendulum
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        render_pendulum(self, painter, pendulum_radius(self.width(), self.height(), self.length_scale))


class AnalysisTrace(QWidget):
    def __init__(self):
        super().__init__()
        self.result = None
        self.setMinimumHeight(100)
        self.setMaximumHeight(140)

    def paintEvent(self, event):
        if self.result is None or not self.result.samples:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        plot = QRectF(10, 24, self.width()-20, self.height()-46)
        baseline = plot.center().y()
        extent = max(1, max(abs(math.degrees(s.angle-s.reference)) for s in self.result.samples))*1.1
        from .simulation import DURATION
        points = [QPointF(plot.left()+s.time/DURATION*plot.width(),
                         baseline-math.degrees(s.angle-s.reference)/extent*plot.height()/2)
                  for s in self.result.samples[::10]]
        last = self.result.samples[-1]
        last_point = QPointF(plot.left()+last.time/DURATION*plot.width(),
                             baseline-math.degrees(last.angle-last.reference)/extent*plot.height()/2)
        if points[-1] != last_point:
            points.append(last_point)
        area = QPainterPath(QPointF(plot.left(), baseline))
        trace = QPainterPath(points[0])
        for point in points:
            area.lineTo(point)
            trace.lineTo(point)
        area.lineTo(QPointF(plot.right(), baseline))
        area.closeSubpath()
        p.fillPath(area, QColor(23, 107, 154, 45))
        p.setPen(QPen(QColor(CYAN), 2))
        p.drawPath(trace)
        p.setPen(QPen(QColor(GREEN), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(plot.left(), baseline), QPointF(plot.right(), baseline))
        p.setFont(QFont(FONT_BODY, 9))
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(10, 0, self.width()-20, 25), "ERROR A LO LARGO DEL TIEMPO")
        bottom = QRectF(10, self.height()-20, self.width()-20, 20)
        p.drawText(bottom, Qt.AlignmentFlag.AlignLeft, "0 s")
        p.drawText(bottom, Qt.AlignmentFlag.AlignRight, f"{DURATION:g} s")


class GainReadout(QWidget):
    def __init__(self):
        super().__init__()
        self.gains = None
        self.setFixedHeight(114)

    def paintEvent(self, event):
        if self.gains is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont(FONT_BODY, 10))
        p.setPen(QColor(MUTED))
        p.drawText(0, 15, "TUS GANANCIAS")
        for i, (name, value, maximum, color) in enumerate((
                ("Kp", self.gains.kp, 10, CYAN), ("Ki", self.gains.ki, 5, BLUE),
                ("Kd", self.gains.kd, 3, GREEN))):
            y = 34+i*26
            p.setPen(QColor(TEXT))
            p.drawText(0, y+5, name)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#dbe6df"))
            p.drawRoundedRect(QRectF(40, y-5, self.width()-120, 8), 4, 4)
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(40, y-5, max(2, (self.width()-120)*value/maximum), 8), 4, 4)
            p.setPen(QColor(color))
            p.drawText(QRectF(self.width()-65, y-12, 65, 25), Qt.AlignmentFlag.AlignRight, f"{value:.2f}")


class ResponseChart(QWidget):
    """Gráfica única y amplia, siempre en escala de recorrido completo."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.view, self.response, self.x, self.y, self.reference = self._chart()
        self.view.setMinimumHeight(260)
        self.view.setMinimumWidth(420)
        self.setMinimumHeight(290)
        layout.addWidget(self.view, 1)
        key = QHBoxLayout()
        key.setSpacing(8)
        for color, caption in ((CYAN, "SALIDA θ(t)"),
                               (GREEN, "REFERENCIA"),
                               (CORAL, "EMPUJÓN")):
            swatch = QFrame()
            swatch.setFixedSize(18, 3)
            swatch.setStyleSheet(f"background: {color}; border-radius: 1px;")
            key.addWidget(swatch)
            text = QLabel(caption)
            text.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 500;")
            key.addWidget(text)
            key.addSpacing(14)
        key.addStretch()
        layout.addLayout(key)
        self.full_extent = 60
        self.last_result = None

    def _chart(self):
        chart = QChart()
        prepare_chart(chart)
        view = QChartView(chart)
        view.setBackgroundBrush(QColor(NAVY))
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        x, y = QValueAxis(), QValueAxis()
        from .simulation import DURATION, STEP_TIME, STEP_DEGREES
        x_min, x_max = -.3, DURATION
        x.setRange(x_min, x_max)
        x.setTickCount(9)
        x.setTickType(QValueAxis.TickType.TicksDynamic)
        x.setTickAnchor(0)
        x.setTickInterval(2)
        x.setLabelFormat("%.0f")
        y.setRange(-20, 60)
        y.setTickCount(5)
        y.setLabelFormat("%.0f")
        x.setTitleText("Tiempo (s)")
        y.setTitleText("Ángulo (°)")
        for axis, alignment in ((x, Qt.AlignmentFlag.AlignBottom), (y, Qt.AlignmentFlag.AlignLeft)):
            chart.addAxis(axis, alignment)
            axis.setLabelsColor(QColor(MUTED))
            axis.setTitleBrush(QColor(MUTED))
            axis.setLabelsFont(QFont(FONT_BODY, 9))
            axis.setTitleFont(QFont(FONT_BODY, 10))
            axis.setGridLineColor(QColor(GRID))
            axis.setLinePen(QPen(QColor("#607d8e"), 1))
        series_list = []

        # Empujón inicial en t = 0 s
        impulse = QLineSeries()
        impulse.append(0, -10000); impulse.append(0, 10000)
        impulse.setPen(QPen(QColor(CORAL), 1.5, Qt.PenStyle.DashLine))
        series_list.append(impulse)

        # Curva de referencia / setpoint: escalón a 45° a los 5 s
        reference = QLineSeries()
        reference.append(x_min, 0); reference.append(STEP_TIME, 0)
        reference.append(STEP_TIME, STEP_DEGREES); reference.append(x_max, STEP_DEGREES)
        reference.setPen(QPen(QColor(GREEN), 1.8, Qt.PenStyle.DashLine))
        series_list.append(reference)

        # Curva de salida del sistema θ(t)
        response = QLineSeries()
        response.setPen(QPen(QColor(CYAN), 2.8))
        series_list.append(response)

        # Cursor puntual en el tiempo actual
        self.cursor = QScatterSeries()
        self.cursor.setColor(QColor("#142b43"))
        self.cursor.setBorderColor(QColor(CYAN))
        self.cursor.setMarkerSize(7)
        series_list.append(self.cursor)

        for series in series_list:
            chart.addSeries(series)
            series.attachAxis(x); series.attachAxis(y)
        return view, response, x, y, reference

    def clear(self):
        self.response.clear()
        self.cursor.clear()
        self.last_result = None
        self.full_extent = 60
        self.y.setRange(-20, 60)

    def reveal(self, result, index):
        if result is not self.last_result:
            min_deg = min(math.degrees(s.angle) for s in result.samples)
            max_deg = max(math.degrees(s.angle) for s in result.samples)
            y_lower = min(-20.0, min_deg * 1.1)
            y_upper = max(60.0, max_deg * 1.1)
            self.y.setRange(y_lower, y_upper)
            self.last_result = result
        points = [QPointF(-.3, 0)]
        points += [QPointF(s.time, math.degrees(s.angle)) for s in result.samples[:index+1:2]]
        sample = result.samples[index]
        if index % 2:
            points.append(QPointF(sample.time, math.degrees(sample.angle)))
        self.response.replace(points)
        self.cursor.replace([QPointF(sample.time, math.degrees(sample.angle))])

