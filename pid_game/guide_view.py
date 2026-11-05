"""Vista pedagógica: ¿Qué es el IAE? y ¿Qué hacen Kp, Ki y Kd?

Proporciona explicaciones conceptuales, gráficas comparativas de 'Antes vs Después'
con aislamiento de variables, y métricas reales calculadas por el motor de física.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from PySide6.QtCore import Qt, QPointF, QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QScrollArea
)
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QAreaSeries, QValueAxis
)

from .controller import Gains
from .simulation import simulate, Result, DURATION, STEP_TIME, STEP_DEGREES
from .theme import MUTED, CYAN, LIME, CORAL, FONT_DISPLAY, FONT_BODY
from .motion import ArcadeButton
from .textos import text


TOPICS = {
    "iae": {
        "tab": "¿Qué es el IAE?",
        "title": "IAE · Error acumulado",
        "subtitle": "El área total del error durante la prueba",
        "concept": (
            "El IAE suma el error angular absoluto durante los 15 s:\n\n"
            "    IAE = ∫ |r(t) − θ(t)| dt   [grados · segundo]\n\n"
            "Menor área significa menor error acumulado."
        ),
        "rules": [
            "Cada segundo de error suma al puntaje.",
            "Desviarse a cualquiera de los dos lados aporta lo mismo.",
            "El ranking ordena por IAE.",
        ],
        "before_label": "Antes: Control deficiente",
        "before_gains": Gains(0.8, 0.05, 0.1),
        "before_desc": "Respuesta con mayor error acumulado.",
        "after_label": "Después: Control calibrado",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Respuesta con menor error acumulado.",
        "alert": "La referencia cambia de 0° a 45° en el segundo 5.",
        "show_area": True,
    },
    "kp": {
        "tab": "Kp · Proporcional",
        "title": "Kp · Acción proporcional",
        "subtitle": "Corrige según el error actual",
        "concept": (
            "Kp genera torque proporcional al error actual:\n\n"
            "    τ_p = Kp · (referencia − θ)"
        ),
        "rules": [
            "Compara Kp=0.40 y 2.50; Ki y Kd quedan fijos.",
            "Más Kp intensifica la corrección.",
            "Un valor alto puede aumentar el sobrepaso o la saturación.",
        ],
        "before_label": "Antes: Kp = 0.40",
        "before_gains": Gains(0.4, 0.8, 0.5),
        "before_desc": "Respuesta con menor Kp.",
        "after_label": "Después: Kp = 2.50",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Respuesta con mayor Kp; Ki y Kd no cambian.",
        "alert": "Aumentar Kp no garantiza menor error en todos los tramos.",
        "show_area": False,
    },
    "ki": {
        "tab": "Ki · Integral",
        "title": "Ki · Acción integral",
        "subtitle": "Acumula el error a lo largo del tiempo",
        "concept": (
            "Ki acumula el error para corregir desviaciones persistentes:\n\n"
            "    τ_i = Ki · ∫ (referencia − θ) dt"
        ),
        "rules": [
            "Compara Ki=0.00 y 0.80; Kp y Kd quedan fijos.",
            "Ki puede reducir el error que persiste.",
            "Un valor excesivo puede causar windup y sobrepaso.",
        ],
        "before_label": "Antes: Ki = 0.00 (Sin memoria)",
        "before_gains": Gains(2.5, 0.0, 0.5),
        "before_desc": "Sin acción integral.",
        "after_label": "Después: Ki = 0.80",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Con acción integral; Kp y Kd no cambian.",
        "alert": "El anti-windup limita la acumulación cuando el actuador satura.",
        "show_area": False,
    },
    "kd": {
        "tab": "Kd · Derivativo",
        "title": "Kd · Acción derivativa",
        "subtitle": "Amortigua usando la velocidad medida",
        "concept": (
            "Kd aplica torque opuesto a la velocidad angular medida. La derivada se filtra:\n\n"
            "    τ_d = −Kd · ω filtrada"
        ),
        "rules": [
            "Compara Kd=0.05 y 0.50; Kp y Ki quedan fijos.",
            "Más Kd suele reducir el rebote.",
            "Demasiado Kd puede volver lenta la respuesta.",
        ],
        "before_label": "Antes: Kd = 0.05",
        "before_gains": Gains(2.5, 0.8, 0.05),
        "before_desc": "Menor amortiguación.",
        "after_label": "Después: Kd = 0.50",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Mayor amortiguación; Kp y Ki no cambian.",
        "alert": "La derivada medida evita el salto que produciría derivar la referencia.",
        "show_area": False,
    },
}

# Los parámetros y las ganancias permanecen aquí; el contenido textual se edita
# en textos_es.json.
for _key in TOPICS:
    for _field in ("tab", "title", "subtitle", "concept", "alert", "before_label", "after_label", "before_desc", "after_desc"):
        TOPICS[_key][_field] = text(f"guide.{_key}.{_field}")
    TOPICS[_key]["rules"][-1] = text(f"guide.{_key}.rule")


class _SimulationSignals(QObject):
    completed = Signal(str, object, object, str)


class _SimulationTask(QRunnable):
    """Calcula un par fuera del hilo de la interfaz; nunca toca widgets."""

    def __init__(self, key: str, topic: dict):
        super().__init__()
        self.key = key
        self.topic = topic
        self.signals = _SimulationSignals()

    def run(self):
        before = after = None
        error = ""
        try:
            before = simulate(self.topic["before_gains"])
            after = simulate(self.topic["after_gains"])
        except Exception as exc:  # pass failures back to the UI thread
            error = f"{type(exc).__name__}: {exc}"
        self.signals.completed.emit(self.key, before, after, error)


class EducationalChart(QWidget):
    """Gráfico interactivo de alta fidelidad para comparativas didácticas."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mode = "before"  # "both", "before", "after"
        self.current_topic: Optional[dict] = None
        self.before_res: Optional[Result] = None
        self.after_res: Optional[Result] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Barra de control superior del gráfico
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)
        self.legend_label = QLabel()
        self.legend_label.setTextFormat(Qt.TextFormat.RichText)
        self._set_legend()
        self.legend_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 600; font-family: '{FONT_BODY}';")
        layout.addWidget(self.legend_label)
        top_bar.addStretch()

        self.btn_both = ArcadeButton(text("guide.both"))
        self.btn_before = ArcadeButton(text("guide.before_only"))
        self.btn_after = ArcadeButton(text("guide.after_only"))
        for b in (self.btn_both, self.btn_before, self.btn_after):
            b.setObjectName("secondary")
            b.setFixedHeight(28)
            b.setStyleSheet("padding: 4px 12px; font-size: 11px; min-height: 20px;")
            top_bar.addWidget(b)

        for button in (self.btn_both, self.btn_before, self.btn_after):
            button.setCheckable(True)
        self.btn_before.setChecked(True)

        self.btn_both.clicked.connect(lambda: self.set_mode("both"))
        self.btn_before.clicked.connect(lambda: self.set_mode("before"))
        self.btn_after.clicked.connect(lambda: self.set_mode("after"))
        layout.addLayout(top_bar)

        # Vista de gráfico QtChart
        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.legend().hide()
        self.chart.setMargins(self.chart.margins())
        self.chart.layout().setContentsMargins(0, 0, 0, 0)

        self.view = QChartView(self.chart)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("border: none; background: #12243a;")
        layout.addWidget(self.view, 1)

        # Ejes
        self.x_axis = QValueAxis()
        self.x_axis.setRange(-0.3, DURATION)
        self.x_axis.setTickType(QValueAxis.TickType.TicksDynamic)
        self.x_axis.setTickAnchor(0)
        self.x_axis.setTickInterval(2)
        self.x_axis.setLabelFormat("%.0f")
        self.x_axis.setTitleText(text("guide.x_axis"))
        self.x_axis.setTitleBrush(QBrush(QColor(MUTED)))
        self.x_axis.setLabelsBrush(QBrush(QColor(MUTED)))
        self.x_axis.setGridLinePen(QPen(QColor(36, 62, 84, 120), 1, Qt.PenStyle.DashLine))
        self.x_axis.setLinePen(QPen(QColor("#607d8e"), 1))
        self.chart.addAxis(self.x_axis, Qt.AlignmentFlag.AlignBottom)

        self.y_axis = QValueAxis()
        self.y_axis.setRange(-20, 70)
        self.y_axis.setTickCount(6)
        # Dejar los ticks numéricos evita que Qt Charts sustituya el glifo °
        # por un carácter de reemplazo en algunos entornos de Windows.
        self.y_axis.setLabelFormat("%.0f")
        self.y_axis.setTitleText(text("guide.y_axis"))
        self.y_axis.setTitleBrush(QBrush(QColor(MUTED)))
        self.y_axis.setLabelsBrush(QBrush(QColor(MUTED)))
        self.y_axis.setGridLinePen(QPen(QColor(36, 62, 84, 120), 1, Qt.PenStyle.DashLine))
        self.y_axis.setLinePen(QPen(QColor("#607d8e"), 1))
        self.chart.addAxis(self.y_axis, Qt.AlignmentFlag.AlignLeft)

        # Series fijas: Referencia y Empujón
        self.ref_series = QLineSeries()
        self.ref_series.setPen(QPen(QColor(LIME), 1.8, Qt.PenStyle.DashLine))
        self.chart.addSeries(self.ref_series)
        self.ref_series.attachAxis(self.x_axis)
        self.ref_series.attachAxis(self.y_axis)

        self.push_series = QLineSeries()
        self.push_series.setPen(QPen(QColor(CORAL), 1.5, Qt.PenStyle.DashLine))
        self.chart.addSeries(self.push_series)
        self.push_series.attachAxis(self.x_axis)
        self.push_series.attachAxis(self.y_axis)

        # Series dinámicas persistentes (evitan recreación y recolección de basura C++)
        self.areas = {}
        for name, color in (("before", CORAL), ("after", CYAN)):
            upper, lower = QLineSeries(), QLineSeries()
            area = QAreaSeries(upper, lower)
            area.setPen(QPen(Qt.PenStyle.NoPen))
            fill = QColor(color)
            fill.setAlpha(65)
            area.setBrush(QBrush(fill))
            self.chart.addSeries(area)
            area.attachAxis(self.x_axis)
            area.attachAxis(self.y_axis)
            area.hide()
            self.areas[name] = (area, upper, lower)

        self.before_series = QLineSeries()
        before_pen = QPen(QColor(CORAL), 2.4, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.before_series.setPen(before_pen)
        self.chart.addSeries(self.before_series)
        self.before_series.attachAxis(self.x_axis)
        self.before_series.attachAxis(self.y_axis)

        self.after_series = QLineSeries()
        after_pen = QPen(QColor(CYAN), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.after_series.setPen(after_pen)
        self.chart.addSeries(self.after_series)
        self.after_series.attachAxis(self.x_axis)
        self.after_series.attachAxis(self.y_axis)

        self._draw_reference_and_push()
        self.set_mode("before")

    def _draw_reference_and_push(self):
        self.ref_series.clear()
        self.ref_series.append(-0.3, 0)
        self.ref_series.append(STEP_TIME, 0)
        self.ref_series.append(STEP_TIME, STEP_DEGREES)
        self.ref_series.append(DURATION, STEP_DEGREES)

        self.push_series.clear()
        # El empujón permanece en la simulación; se omite su marcador aquí
        # para no confundirlo con la curva de la comparativa anterior.

    def _set_legend(self):
        self.legend_label.setText(
            f'{text("guide.legend_curves")} <span style="color:{CORAL};">┄┄ {text("guide.legend_before")}</span>'
            f' &nbsp; <span style="color:{CYAN};">━━ {text("guide.legend_after")}</span>'
            f' &nbsp; <span style="color:{LIME};">┄┄ {text("guide.legend_reference")}</span>'
            + (f' &nbsp; <span style="color:{CORAL};">■ {text("guide.legend_area_before")}</span>'
               f' &nbsp; <span style="color:{CYAN};">■ {text("guide.legend_area_after")}</span>'
               if self.current_topic and self.current_topic.get("show_area") else "")
        )

    def clear_scenario(self):
        """Oculta las series mientras se calcula la pestaña seleccionada."""
        self.current_topic = None
        self.before_res = None
        self.after_res = None
        self.before_series.clear()
        self.after_series.clear()
        for _, upper, lower in self.areas.values():
            upper.clear()
            lower.clear()
        self._set_series_visibility()
        self.legend_label.setText(f"<span style=\"color:{MUTED};\">Preparando comparativa…</span>")

    def set_mode(self, mode: str):
        if mode not in ("both", "before", "after"):
            mode = "both"
        self.mode = mode
        self.btn_both.setChecked(mode == "both")
        self.btn_before.setChecked(mode == "before")
        self.btn_after.setChecked(mode == "after")
        # Resaltar botón activo
        for button, button_mode in ((self.btn_both, "both"), (self.btn_before, "before"), (self.btn_after, "after")):
            active = button_mode == mode
            button.setStyleSheet(
                "padding: 4px 12px; font-size: 11px; min-height: 20px; "
                + ("background: #1c364e; border: 1px solid #5dd8f0;" if active else "")
            )
        self._set_series_visibility()

    def render_scenario(self, topic: dict, before_res: Result, after_res: Result):
        self.current_topic = topic
        self.before_res = before_res
        self.after_res = after_res
        self._set_legend()

        # Ajustar el eje una vez por tema. El pico conserva la escala completa,
        # incluso si el modo visible muestra una sola curva.
        angles = [math.degrees(sample.angle) for result in (before_res, after_res) for sample in result.samples]
        self.y_axis.setRange(min(-20.0, min(angles) * 1.1), max(60.0, max(angles) * 1.1))

        # Limitar la geometría que llega a Qt Charts. El motor conserva todas
        # las muestras para IAE y métricas; la curva y el sombreado son una vista.
        self.before_series.clear()
        before_samples = self._plot_samples(before_res.samples, 1800, preserve_step=True)
        points = [QPointF(s.time, math.degrees(s.angle)) for s in before_samples]
        self.before_series.append(points)

        self.after_series.clear()
        after_samples = self._plot_samples(after_res.samples, 1800, preserve_step=True)
        points = [QPointF(s.time, math.degrees(s.angle)) for s in after_samples]
        self.after_series.append(points)

        # Cada curva tiene su propia área entre la respuesta y la referencia.
        for name, result in (("before", before_res), ("after", after_res)):
            _, upper, lower = self.areas[name]
            upper.clear()
            lower.clear()
            if topic.get("show_area"):
                top_pts, bot_pts = [], []
                for sample in self._plot_samples(result.samples, 240, preserve_step=True):
                    deg = math.degrees(sample.angle)
                    ref = math.degrees(sample.reference)
                    top_pts.append(QPointF(sample.time, max(deg, ref)))
                    bot_pts.append(QPointF(sample.time, min(deg, ref)))
                upper.append(top_pts)
                lower.append(bot_pts)
        self._set_series_visibility()

    @staticmethod
    def _plot_samples(samples, max_points: int, preserve_step: bool = False):
        if len(samples) <= max_points:
            return samples
        stride = max(1, math.ceil((len(samples) - 1) / max(1, max_points - 1)))
        indexes = set(range(0, len(samples), stride))
        indexes.add(len(samples) - 1)
        if preserve_step and len(samples) > 1:
            sample_dt = samples[1].time - samples[0].time
            step_index = round(STEP_TIME / sample_dt)
            indexes.update(i for i in (step_index - 1, step_index) if 0 <= i < len(samples))
        return [samples[index] for index in sorted(indexes)]

    def _set_series_visibility(self):
        has_result = self.before_res is not None and self.after_res is not None
        self.before_series.setVisible(has_result and self.mode in ("both", "before"))
        self.after_series.setVisible(has_result and self.mode in ("both", "after"))
        for name, (area, _, _) in self.areas.items():
            area.setVisible(bool(
                has_result and self.current_topic
                and self.current_topic.get("show_area")
                and self.mode in ("both", name)
            ))


class EducationalGuidePage(QWidget):
    """Página didáctica completa integrada en el QStackedWidget de MainWindow."""

    preload_progress = Signal(int, int, str)

    def __init__(self, on_back: Callable[[], None], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.on_back = on_back
        self.presets: dict[str, tuple[Result, Result]] = {}
        self._tasks: dict[str, _SimulationTask] = {}
        self._pending_keys: list[str] = []
        self._running_key: Optional[str] = None
        self.current_topic_key = "iae"
        self._preloading = False
        self._preload_done: set[str] = set()
        self._preload_errors: dict[str, str] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # 1. Cabecera superior: Título general y botón Volver
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel(text("guide.title"))
        lbl_title.setStyleSheet(f"font-family: '{FONT_DISPLAY}'; font-size: 20px; font-weight: 700; color: #eaf5fc; letter-spacing: 1px;")
        lbl_sub = QLabel(text("guide.subtitle"))
        lbl_sub.setStyleSheet(f"color: {MUTED}; font-size: 13px; font-family: '{FONT_BODY}';")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box, 1)

        self.btn_back = ArcadeButton(text("guide.back"))
        self.btn_back.setObjectName("secondary")
        self.btn_back.clicked.connect(self.on_back)
        header.addWidget(self.btn_back)
        outer.addLayout(header)

        # 2. Barra de pestañas temática
        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(10)
        self.tab_buttons: dict[str, QPushButton] = {}
        self.tab_group = QButtonGroup(self)

        for key, info in TOPICS.items():
            btn = ArcadeButton(info["tab"])
            btn.setObjectName("secondary")
            btn.setFixedHeight(36)
            btn.setStyleSheet("font-size: 13px; font-weight: 600; padding: 6px 16px;")
            self.tab_buttons[key] = btn
            btn.setCheckable(True)
            self.tab_group.addButton(btn)
            tabs_layout.addWidget(btn)
            btn.clicked.connect(lambda _, k=key: self.select_tab(k))

        tabs_layout.addStretch()
        outer.addLayout(tabs_layout)

        # 3. Contenedor principal dividido en dos columnas: Explicación (izq) y Gráfica (der)
        main_split = QHBoxLayout()
        main_split.setSpacing(18)

        # Columna Izquierda: Tarjetas explicativas con scroll
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setStyleSheet("background: transparent;")
        left_widget = QWidget()
        self.left_layout = QVBoxLayout(left_widget)
        self.left_layout.setContentsMargins(0, 0, 10, 0)
        self.left_layout.setSpacing(12)

        # Elementos de texto dinámicos
        self.lbl_topic_title = QLabel()
        self.lbl_topic_title.setWordWrap(True)
        self.lbl_topic_title.setStyleSheet(f"font-family: '{FONT_DISPLAY}'; font-size: 18px; font-weight: 700; color: {CYAN};")
        self.left_layout.addWidget(self.lbl_topic_title)

        self.lbl_topic_sub = QLabel()
        self.lbl_topic_sub.setWordWrap(True)
        self.lbl_topic_sub.setStyleSheet(f"color: #e4f2f8; font-size: 13px; font-weight: 500; font-family: '{FONT_BODY}';")
        self.left_layout.addWidget(self.lbl_topic_sub)

        # Caja de concepto principal
        self.frame_concept = QFrame()
        self.frame_concept.setStyleSheet("background: transparent; border: none;")
        v_concept = QVBoxLayout(self.frame_concept)
        v_concept.setContentsMargins(0, 0, 0, 0)
        self.lbl_concept = QLabel()
        self.lbl_concept.setWordWrap(True)
        self.lbl_concept.setStyleSheet("color: #cfdbe6; font-size: 12px; line-height: 1.4;")
        v_concept.addWidget(self.lbl_concept)
        self.left_layout.addWidget(self.frame_concept)

        self.lbl_rules = QLabel()
        self.lbl_rules.setWordWrap(True)
        self.lbl_rules.setStyleSheet("color: #cfdbe6; font-size: 12px;")
        self.left_layout.addWidget(self.lbl_rules)

        # Caja de métricas Antes vs Después
        self.frame_metrics = QFrame()
        self.frame_metrics.setObjectName("guideMetrics")
        self.frame_metrics.setStyleSheet("QFrame#guideMetrics { background: transparent; border: none; border-top: 1px solid #28445c; }")
        v_metrics = QVBoxLayout(self.frame_metrics)
        v_metrics.setContentsMargins(0, 14, 0, 0)
        v_metrics.setSpacing(10)

        lbl_comp_title = QLabel(text("guide.compare"))
        lbl_comp_title.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        v_metrics.addWidget(lbl_comp_title)

        self.lbl_before_metric = QLabel()
        self.lbl_before_metric.setWordWrap(True)
        self.lbl_before_metric.setStyleSheet("color: #cfdbe6; font-size: 12px;")
        v_metrics.addWidget(self.lbl_before_metric)

        self.lbl_after_metric = QLabel()
        self.lbl_after_metric.setWordWrap(True)
        self.lbl_after_metric.setStyleSheet("color: #cfdbe6; font-size: 12px;")
        v_metrics.addWidget(self.lbl_after_metric)
        self.left_layout.addWidget(self.frame_metrics)

        # Caja de Alerta / Consejo
        self.frame_alert = QFrame()
        self.frame_alert.setObjectName("guideAlert")
        self.frame_alert.setStyleSheet("QFrame#guideAlert { background: transparent; border: none; border-left: 2px solid #5dd8f0; }")
        v_alert = QVBoxLayout(self.frame_alert)
        v_alert.setContentsMargins(12, 2, 0, 2)
        self.lbl_alert = QLabel()
        self.lbl_alert.setWordWrap(True)
        self.lbl_alert.setStyleSheet("color: #d8edf7; font-size: 12px; font-weight: 500;")
        v_alert.addWidget(self.lbl_alert)
        self.left_layout.addWidget(self.frame_alert)

        self.left_layout.addStretch()
        left_scroll.setWidget(left_widget)
        main_split.addWidget(left_scroll, 4)

        # Columna Derecha: Gráfico didáctico
        self.chart_view = EducationalChart()
        main_split.addWidget(self.chart_view, 6)

        outer.addLayout(main_split, 1)

        # Seleccionar la primera pestaña por defecto
        self.select_tab("iae")

    def preload_all(self):
        """Prepara las cuatro comparativas sin bloquear el hilo de interfaz."""
        if self._preloading:
            return
        self._preloading = True
        self._preload_done = set(self.presets)
        self._preload_errors.clear()
        self.preload_progress.emit(len(self._preload_done), len(TOPICS), "")
        for key in TOPICS:
            if key not in self._preload_done and key != self._running_key and key not in self._pending_keys:
                self._pending_keys.append(key)
        if len(self._preload_done) == len(TOPICS):
            self._preloading = False
        else:
            self._start_next_simulation()

    def cancel_preload(self):
        """Descarta trabajo pendiente; la tarea activa termina por sí sola."""
        self._preloading = False
        self._pending_keys.clear()

    def _precompute_simulations(self):
        """Compatibilidad interna: encola la pestaña visible sin bloquear Qt."""
        self._ensure_simulation(self.current_topic_key)

    def showEvent(self, event):
        super().showEvent(event)
        self._ensure_simulation(self.current_topic_key)

    def hideEvent(self, event):
        # No empezar trabajo pendiente si el usuario ya volvió a otra pantalla.
        if not self._preloading:
            self._pending_keys.clear()
        super().hideEvent(event)

    def _ensure_simulation(self, key: str):
        if key in self.presets or key == self._running_key:
            return
        if key in self._pending_keys:
            # Priorizar la pestaña que el usuario acaba de seleccionar.
            self._pending_keys.remove(key)
            self._pending_keys.insert(0, key)
        elif key not in self._tasks:
            self._pending_keys.insert(0, key)
        self._start_next_simulation()

    def _start_next_simulation(self):
        if (not self.isVisible() and not self._preloading) or self._running_key is not None or not self._pending_keys:
            return
        key = self._pending_keys.pop(0)
        task = _SimulationTask(key, TOPICS[key])
        task.signals.completed.connect(self._on_simulation_completed)
        self._tasks[key] = task
        self._running_key = key
        QThreadPool.globalInstance().start(task)

    def _on_simulation_completed(self, key: str, before, after, error: str):
        self._tasks.pop(key, None)
        if self._running_key == key:
            self._running_key = None

        if not error and before is not None and after is not None:
            self.presets[key] = (before, after)
            if key == self.current_topic_key and self.isVisible():
                self._show_topic_results(key)
        elif key == self.current_topic_key:
            self.lbl_before_metric.setText(text("guide.error"))
            self.lbl_after_metric.clear()
            self.chart_view.clear_scenario()
            self.chart_view.legend_label.setText(text("guide.unavailable"))

        if self._preloading:
            self._preload_done.add(key)
            if error or before is None or after is None:
                self._preload_errors[key] = error or "No se obtuvo un resultado"
            summary = "; ".join(f"{name}: {message}" for name, message in self._preload_errors.items())
            self.preload_progress.emit(len(self._preload_done), len(TOPICS), summary)
            if len(self._preload_done) == len(TOPICS):
                self._preloading = False

        self._start_next_simulation()

    def select_tab(self, key: str):
        if key not in TOPICS:
            key = "iae"
        info = TOPICS[key]
        self.current_topic_key = key

        # Resaltar botón de pestaña activo
        for k, btn in self.tab_buttons.items():
            btn.setChecked(k == key)
            if k == key:
                btn.setStyleSheet("background: #1c364e; border: 1.5px solid #5dd8f0; color: #5dd8f0; font-weight: 700; border-radius: 6px;")
            else:
                btn.setStyleSheet("background: #13273a; border: 1px solid #28445c; color: #e4f2f8; font-weight: 600; border-radius: 6px;")

        # Actualizar textos
        self.lbl_topic_title.setText(info["title"])
        self.lbl_topic_sub.setText(info["subtitle"])
        self.lbl_concept.setText(info["concept"])
        self.lbl_rules.setText(info["rules"][-1])
        self.lbl_alert.setText(info["alert"])

        # Mostrar el contenido conceptual de inmediato y cargar simulaciones
        # solo al necesitar la pestaña, fuera del hilo de la interfaz.
        self.lbl_before_metric.setText(text("guide.loading"))
        self.lbl_after_metric.clear()
        self.chart_view.set_mode("before")
        self.chart_view.clear_scenario()
        if key in self.presets:
            self._show_topic_results(key)
        elif self.isVisible():
            self._ensure_simulation(key)

    def _show_topic_results(self, key: str):
        info = TOPICS[key]
        b_res, a_res = self.presets[key]
        # Solo se revela la ganancia que se estudia en la pestaña.
        def metric(label, result, color):
            return f"<b style='color:{color};'>{label}</b><br>IAE = {result.iae:.1f} pts"

        self.lbl_before_metric.setText(metric(info["before_label"], b_res, CORAL))
        self.lbl_after_metric.setText(metric(info["after_label"], a_res, CYAN))

        self.lbl_alert.setText(info["alert"])
        self.chart_view.render_scenario(info, b_res, a_res)
