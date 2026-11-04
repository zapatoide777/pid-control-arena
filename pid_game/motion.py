"""Animaciones de presentación: no intervienen en el cálculo ni el reloj del juego."""
from PySide6.QtCore import Property, QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QWidget
from .theme import CYAN, LIME, LINE

_accessibility_refs = None


def _accessibility_hints():
    """Mantener vivos los wrappers PySide de ambos objetos relacionados."""
    global _accessibility_refs
    app = QGuiApplication.instance()
    if app is None:
        _accessibility_refs = None
        return None
    if _accessibility_refs is None or _accessibility_refs[0] is not app:
        hints = app.styleHints()
        accessor = getattr(hints, "accessibility", None)
        accessibility = accessor() if accessor is not None else None
        _accessibility_refs = (app, hints, accessibility)
    return _accessibility_refs[2]


def reduced_motion():
    """Preferencia del sistema en Qt 6.12; versiones previas no la exponen."""
    accessibility = _accessibility_hints()
    if accessibility is None or not hasattr(Qt, "MotionPreference"):
        return False
    return accessibility.motionPreference() == Qt.MotionPreference.ReducedMotion


def on_motion_change(callback):
    accessibility = _accessibility_hints()
    if accessibility is not None:
        accessibility.motionPreferenceChanged.connect(callback)


class ArcadeButton(QPushButton):
    """Mantiene el comportamiento nativo del botón y añade luz al interactuar."""
    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = 0.0
        self._press = 0.0
        self._keyboard_focus = False
        self.hover_animation = QPropertyAnimation(self, b"hoverLevel", self)
        self.hover_animation.setDuration(220)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.press_animation = QPropertyAnimation(self, b"pressLevel", self)
        self.press_animation.setDuration(130)
        self.press_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.pressed.connect(lambda: self._animate(self.press_animation, self._press, 1.0))
        self.released.connect(lambda: self._animate(self.press_animation, self._press, 0.0))
        on_motion_change(self._motion_changed)

    def _motion_changed(self, preference):
        if preference == Qt.MotionPreference.ReducedMotion:
            self.hover_animation.stop()
            self.press_animation.stop()
            self._set_hover(float(self.underMouse() and self.isEnabled()))
            self._set_press(float(self.isDown() and self.isEnabled()))

    def _animate(self, animation, current, target):
        animation.stop()
        if reduced_motion():
            if animation is self.hover_animation:
                self._set_hover(target)
            else:
                self._set_press(target)
            return
        animation.setStartValue(current)
        animation.setEndValue(target)
        animation.start()

    def _get_hover(self): return self._hover
    def _set_hover(self, value):
        self._hover = float(value)
        self.update()
    hoverLevel = Property(float, _get_hover, _set_hover)

    def _get_press(self): return self._press
    def _set_press(self, value):
        self._press = float(value)
        self.update()
    pressLevel = Property(float, _get_press, _set_press)

    def enterEvent(self, event):
        if self.isEnabled():
            self._animate(self.hover_animation, self._hover, 1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate(self.hover_animation, self._hover, 0.0)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() != Qt.FocusReason.MouseFocusReason
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        self._keyboard_focus = False
        super().focusOutEvent(event)
        self.update()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self.hover_animation.stop()
            self.press_animation.stop()
            self._set_hover(0.0)
            self._set_press(0.0)
        super().changeEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        focused = self.hasFocus() and self._keyboard_focus
        if not self.isEnabled() or (self._hover <= 0 and self._press <= 0 and not focused):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        # Sutil capa de iluminación al pasar el ratón, sin bordes dobles ni líneas inferiores
        if self._hover > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, round(24 * self._hover)))
            p.drawRoundedRect(rect, 5.0, 5.0)
        # Atenuación suave al presionar
        if self._press > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, round(35 * self._press)))
            p.drawRoundedRect(rect, 5.0, 5.0)
        # Indicador de foco limpio por teclado: contorno continuo sin línea punteada interior
        if focused:
            focus_pen = QColor(CYAN)
            p.setPen(QPen(focus_pen, 1.6, Qt.PenStyle.SolidLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, 5.0, 5.0)


class ReportSweep(QWidget):
    """Un trazo luminoso recorre la cabecera del resultado una sola vez."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(8)
        self._progress = 1.0
        self.animation = QPropertyAnimation(self, b"progress", self)
        self.animation.setDuration(1100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        on_motion_change(self._motion_changed)

    def _motion_changed(self, preference):
        if preference == Qt.MotionPreference.ReducedMotion:
            self.animation.stop()
            self._set_progress(1.0)

    def _get_progress(self): return self._progress
    def _set_progress(self, value):
        self._progress = float(value)
        self.update()
    progress = Property(float, _get_progress, _set_progress)

    def play(self):
        self.animation.stop()
        if reduced_motion():
            self._set_progress(1.0)
            return
        self._set_progress(0.0)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.height()/2
        p.setPen(QPen(QColor(LINE), 1))
        p.drawLine(QPointF(0, y), QPointF(self.width(), y))
        x = self.width()*self._progress
        if x <= 0:
            return
        gradient = QLinearGradient(max(0, x-180), 0, max(1, x), 0)
        gradient.setColorAt(0, QColor(80, 216, 240, 20))
        gradient.setColorAt(1, QColor(174, 244, 110, 240))
        p.setPen(QPen(gradient, 2))
        p.drawLine(QPointF(0, y), QPointF(x, y))
        if self._progress < .995:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(202, 255, 151, 200))
            p.drawEllipse(QPointF(x, y), 3, 3)
