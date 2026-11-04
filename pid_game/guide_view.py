"""Vista pedagógica: ¿Qué es el IAE? y ¿Qué hacen Kp, Ki y Kd?

Proporciona explicaciones conceptuales, gráficas comparativas de 'Antes vs Después'
con aislamiento de variables, y métricas reales calculadas por el motor de física.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QFont, QPen, QBrush, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QButtonGroup, QScrollArea, QSizePolicy
)
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QAreaSeries, QValueAxis
)

from .controller import Gains
from .simulation import simulate, Result, DURATION, STEP_TIME, STEP_DEGREES
from .theme import BG, TEXT, MUTED, CYAN, LIME, CORAL, FONT_DISPLAY, FONT_BODY, FONT_DATA
from .motion import ArcadeButton


TOPICS = {
    "iae": {
        "tab": "📊  ¿Qué es el IAE?",
        "title": "IAE: Puntuación y Área de Error",
        "subtitle": "Integral of Absolute Error · La métrica que define tu podio",
        "concept": (
            "El IAE mide la desviación total acumulada entre la posición real del péndulo θ(t) "
            "y la referencia deseada durante los 15 segundos de simulación:\n\n"
            "    IAE = ∫ |r(t) - θ(t)| dt   [grados · segundo]\n\n"
            "Visualmente, el puntaje equivale al área sombreada entre tu curva y la meta."
        ),
        "rules": [
            "Menor puntaje es mejor: un control perfecto acumula mínima área (< 50 pts).",
            "Penalización simétrica: pasarse o quedarse corto por 5° suma exactamente lo mismo.",
            "El error sostenido arruina el puntaje: estar desviado 11° durante 10 s suma 110 pts directos.",
            "La caída descalifica: sobrepasar los ±90° impide clasificar al ranking.",
        ],
        "before_label": "Antes: Control deficiente",
        "before_gains": Gains(0.8, 0.05, 0.1),
        "before_desc": "Oscilaciones prolongadas y lenta corrección (gran área acumulada)",
        "after_label": "Después: Control calibrado",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Rápido acoplamiento a la meta con mínima área de penalización",
        "alert": "💡 Consejo docente: Para bajar tu IAE, busca llegar rápido a los 45° y amortiguar sin sobrepico ni rebotes.",
        "show_area": True,
    },
    "kp": {
        "tab": "⚡  Kp · Proporcional",
        "title": "Parámetro Kp · La Fuerza de Reacción",
        "subtitle": "Genera torque directamente proporcional al error presente",
        "concept": (
            "Kp actúa como un resorte torsional. Aplica una fuerza proporcional a la distancia a la meta:\n\n"
            "    τ_p = Kp · (referencia - θ)\n\n"
            "Cuanto más lejos esté la barra de la meta, con más fuerza empuja el motor."
        ),
        "rules": [
            "Aporte principal: Levanta la barra y se opone al empujón inicial de 2 rad/s.",
            "Aislamiento de variables: Se comparan Kp=0.40 vs Kp=2.50 manteniendo Ki=0.80 y Kd=0.50 fijos.",
            "Efecto visual: Un Kp adecuado reacciona de inmediato y acorta el tiempo de subida.",
        ],
        "before_label": "Antes: Kp = 0.40 (Demasiado débil)",
        "before_gains": Gains(0.4, 0.8, 0.5),
        "before_desc": "El motor no vence el empujón inicial ni la gravedad; la barra cae desplomada",
        "after_label": "Después: Kp = 2.50 (Fuerza adecuada)",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Absorbe el impacto en < 2 s y eleva la barra con rapidez hacia los 45°",
        "alert": "⚠️ Riesgo de exceso: Si Kp > 6.0, el motor satura su voltaje (±12 V) y causa oscilaciones destructivas.",
        "show_area": False,
    },
    "ki": {
        "tab": "🔄  Ki · Integral",
        "title": "Parámetro Ki · La Memoria contra la Gravedad",
        "subtitle": "Acumula el error en el tiempo para eliminar el desvío permanente",
        "concept": (
            "Ki tiene memoria histórica. Suma el error que persiste en el tiempo:\n\n"
            "    τ_i = Ki · ∫ (referencia - θ) dt\n\n"
            "Su misión indispensable es sostener la barra inclinada a 45° contra la fuerza de gravedad."
        ),
        "rules": [
            "Física real a 45°: La gravedad ejerce un torque constante de ~0.416 N·m.",
            "Sin Ki (Ki = 0.00): El motor solo genera fuerza si hay error; queda estancado en 56.2° (+11.2° de error continuo).",
            "Con Ki (Ki = 0.80): La integral acumula fuerza y anula totalmente el desvío, clavando 45.0° exactos.",
        ],
        "before_label": "Antes: Ki = 0.00 (Sin memoria)",
        "before_gains": Gains(2.5, 0.0, 0.5),
        "before_desc": "Estancado en 56.2° (error permanente de +11.2° que viola la tolerancia)",
        "after_label": "Después: Ki = 0.80 (Cero error estacionario)",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Anula el error residual por completo, llevando la barra a 45.0° exactos",
        "alert": "⚠️ Riesgo de exceso: Un Ki desmedido (> 2.0) acumula demasiada inercia (windup) y produce sobrepaso excesivo.",
        "show_area": False,
    },
    "kd": {
        "tab": "🛡️  Kd · Derivativo",
        "title": "Parámetro Kd · El Freno Amortiguador",
        "subtitle": "Anticipa el movimiento observando la velocidad para evitar rebotes",
        "concept": (
            "Kd mide la velocidad angular de la barra y aplica un torque contrario:\n\n"
            "    τ_d = -Kd · ω\n\n"
            "Funciona como un amortiguador viscoso inteligente que frena la barra cuando viaja rápido."
        ),
        "rules": [
            "Anticipación: Predice hacia dónde va el péndulo y frena antes de que se pase de la meta.",
            "Sin Kd (Kd = 0.05): El sistema es subamortiguado; al subir a 45° rebota violentamente hasta caer.",
            "Con Kd (Kd = 0.50): Asienta la barra suavemente en la referencia sin sobrepico ni oscilaciones.",
        ],
        "before_label": "Antes: Kd = 0.05 (Subamortiguado)",
        "before_gains": Gains(2.5, 0.8, 0.05),
        "before_desc": "Rebotes violentos de resonancia al cambiar de posición hasta perder el equilibrio",
        "after_label": "Después: Kd = 0.50 (Amortiguación óptima)",
        "after_gains": Gains(2.5, 0.8, 0.5),
        "after_desc": "Frenado suave y seguro al aproximarse a los 45°, logrando estabilidad limpia",
        "alert": "⚠️ Riesgo de exceso: Un Kd exagerado (> 2.0) vuelve al péndulo pesado y lento para reaccionar.",
        "show_area": False,
    },
}


class EducationalChart(QWidget):
    """Gráfico interactivo de alta fidelidad para comparativas didácticas."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mode = "both"  # "both", "before", "after"
        self.current_topic: Optional[dict] = None
        self.before_res: Optional[Result] = None
        self.after_res: Optional[Result] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Barra de control superior del gráfico
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)
        self.legend_label = QLabel("CURVAS:  🔴 ANTES (PROBLEMA)   vs   🔵 DESPUÉS (SOLUCIÓN)")
        self.legend_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 600; font-family: '{FONT_BODY}';")
        top_bar.addWidget(self.legend_label)
        top_bar.addStretch()

        self.btn_both = ArcadeButton("Ambas superpuestas")
        self.btn_before = ArcadeButton("Solo Antes")
        self.btn_after = ArcadeButton("Solo Después")
        for b in (self.btn_both, self.btn_before, self.btn_after):
            b.setObjectName("secondary")
            b.setFixedHeight(28)
            b.setStyleSheet("padding: 4px 12px; font-size: 11px; min-height: 20px;")
            top_bar.addWidget(b)

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
        self.view.setStyleSheet("border: 1px solid #1a334b; border-radius: 6px; background: #12243a;")
        layout.addWidget(self.view, 1)

        # Ejes
        self.x_axis = QValueAxis()
        self.x_axis.setRange(-0.3, DURATION)
        self.x_axis.setTickCount(9)
        self.x_axis.setLabelFormat("%.0f s")
        self.x_axis.setTitleText("Tiempo (s)")
        self.x_axis.setTitleBrush(QBrush(QColor(MUTED)))
        self.x_axis.setLabelsBrush(QBrush(QColor(MUTED)))
        self.x_axis.setGridLinePen(QPen(QColor(36, 62, 84, 120), 1, Qt.PenStyle.DashLine))
        self.x_axis.setLinePen(QPen(QColor("#607d8e"), 1))
        self.chart.addAxis(self.x_axis, Qt.AlignmentFlag.AlignBottom)

        self.y_axis = QValueAxis()
        self.y_axis.setRange(-20, 70)
        self.y_axis.setTickCount(6)
        self.y_axis.setLabelFormat("%.0f°")
        self.y_axis.setTitleText("Ángulo (°)")
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
        self.area_upper = QLineSeries()
        self.area_lower = QLineSeries()
        self.area_series = QAreaSeries(self.area_upper, self.area_lower)
        self.area_series.setPen(QPen(Qt.PenStyle.NoPen))
        self.area_series.setBrush(QBrush(QColor(93, 216, 240, 45)))
        self.chart.addSeries(self.area_series)
        self.area_series.attachAxis(self.x_axis)
        self.area_series.attachAxis(self.y_axis)
        self.area_series.hide()

        self.before_series = QLineSeries()
        self.before_series.setPen(QPen(QColor(CORAL), 2.2, Qt.PenStyle.DashLine))
        self.chart.addSeries(self.before_series)
        self.before_series.attachAxis(self.x_axis)
        self.before_series.attachAxis(self.y_axis)

        self.after_series = QLineSeries()
        self.after_series.setPen(QPen(QColor(CYAN), 2.8, Qt.PenStyle.SolidLine))
        self.chart.addSeries(self.after_series)
        self.after_series.attachAxis(self.x_axis)
        self.after_series.attachAxis(self.y_axis)

        self._draw_reference_and_push()

    def _draw_reference_and_push(self):
        self.ref_series.clear()
        self.ref_series.append(-0.3, 0)
        self.ref_series.append(STEP_TIME, 0)
        self.ref_series.append(STEP_TIME, STEP_DEGREES)
        self.ref_series.append(DURATION, STEP_DEGREES)

        self.push_series.clear()
        self.push_series.append(0, -1000)
        self.push_series.append(0, 1000)

    def set_mode(self, mode: str):
        self.mode = mode
        # Resaltar botón activo
        self.btn_both.setStyleSheet("background: #1c364e; border-color: #5dd8f0;" if mode == "both" else "")
        self.btn_before.setStyleSheet("background: #1c364e; border-color: #5dd8f0;" if mode == "before" else "")
        self.btn_after.setStyleSheet("background: #1c364e; border-color: #5dd8f0;" if mode == "after" else "")
        self._refresh_curves()

    def render_scenario(self, topic: dict, before_res: Result, after_res: Result):
        self.current_topic = topic
        self.before_res = before_res
        self.after_res = after_res
        self._refresh_curves()

    def _refresh_curves(self):
        if not self.before_res or not self.after_res or not self.current_topic:
            return

        # Ajuste adaptativo del eje Y según picos de las curvas a mostrar
        all_samples = []
        if self.mode in ("both", "before"):
            all_samples.extend(self.before_res.samples)
        if self.mode in ("both", "after"):
            all_samples.extend(self.after_res.samples)

        if all_samples:
            min_deg = min(math.degrees(s.angle) for s in all_samples)
            max_deg = max(math.degrees(s.angle) for s in all_samples)
            y_min = min(-25.0, min_deg * 1.15)
            y_max = max(70.0, max_deg * 1.15)
            self.y_axis.setRange(y_min, y_max)

        # Curva Antes (problema)
        self.before_series.clear()
        if self.mode in ("both", "before"):
            points = [QPointF(s.time, math.degrees(s.angle)) for s in self.before_res.samples[::3]]
            self.before_series.append(points)
            self.before_series.show()
        else:
            self.before_series.hide()

        # Curva Después (solución)
        self.after_series.clear()
        if self.mode in ("both", "after"):
            points = [QPointF(s.time, math.degrees(s.angle)) for s in self.after_res.samples[::3]]
            self.after_series.append(points)
            self.after_series.show()
        else:
            self.after_series.hide()

        # Sombreado de área para IAE
        self.area_upper.clear()
        self.area_lower.clear()
        if self.current_topic.get("show_area") and self.mode in ("both", "after"):
            top_pts = []
            bot_pts = []
            for s in self.after_res.samples[::4]:
                deg = math.degrees(s.angle)
                ref = math.degrees(s.reference)
                top_pts.append(QPointF(s.time, max(deg, ref)))
                bot_pts.append(QPointF(s.time, min(deg, ref)))
            self.area_upper.append(top_pts)
            self.area_lower.append(bot_pts)
            self.area_series.show()
        else:
            self.area_series.hide()


class EducationalGuidePage(QWidget):
    """Página didáctica completa integrada en el QStackedWidget de MainWindow."""

    def __init__(self, on_back: Callable[[], None], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.on_back = on_back
        self.presets: dict[str, tuple[Result, Result]] = {}
        self._precompute_simulations()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # 1. Cabecera superior: Título general y botón Volver
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("GUÍA DIDÁCTICA · CONTROL PID & IAE")
        lbl_title.setStyleSheet(f"font-family: '{FONT_DISPLAY}'; font-size: 20px; font-weight: 700; color: #eaf5fc; letter-spacing: 1px;")
        lbl_sub = QLabel("Conceptos físicos, métricas y comparativas de sintonización con el motor no lineal")
        lbl_sub.setStyleSheet(f"color: {MUTED}; font-size: 13px; font-family: '{FONT_BODY}';")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box, 1)

        self.btn_back = ArcadeButton("←  Volver al menú")
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
        self.lbl_topic_title.setStyleSheet(f"font-family: '{FONT_DISPLAY}'; font-size: 18px; font-weight: 700; color: {CYAN};")
        self.left_layout.addWidget(self.lbl_topic_title)

        self.lbl_topic_sub = QLabel()
        self.lbl_topic_sub.setWordWrap(True)
        self.lbl_topic_sub.setStyleSheet(f"color: #e4f2f8; font-size: 13px; font-weight: 500; font-family: '{FONT_BODY}';")
        self.left_layout.addWidget(self.lbl_topic_sub)

        # Caja de concepto principal
        self.frame_concept = QFrame()
        self.frame_concept.setStyleSheet("background: #102238; border: 1px solid #1a334b; border-radius: 6px; padding: 12px;")
        v_concept = QVBoxLayout(self.frame_concept)
        v_concept.setContentsMargins(8, 8, 8, 8)
        self.lbl_concept = QLabel()
        self.lbl_concept.setWordWrap(True)
        self.lbl_concept.setStyleSheet("color: #cfdbe6; font-size: 12px; line-height: 1.4;")
        v_concept.addWidget(self.lbl_concept)
        self.left_layout.addWidget(self.frame_concept)

        # Caja de métricas Antes vs Después
        self.frame_metrics = QFrame()
        self.frame_metrics.setStyleSheet("background: #0d1e30; border: 1px solid #1a334b; border-radius: 6px; padding: 12px;")
        v_metrics = QVBoxLayout(self.frame_metrics)
        v_metrics.setContentsMargins(8, 8, 8, 8)
        v_metrics.setSpacing(10)

        lbl_comp_title = QLabel("COMPARATIVA DE DESEMPEÑO")
        lbl_comp_title.setStyleSheet(f"color: {MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        v_metrics.addWidget(lbl_comp_title)

        self.lbl_before_metric = QLabel()
        self.lbl_before_metric.setWordWrap(True)
        self.lbl_before_metric.setStyleSheet(f"color: {CORAL}; font-size: 12px; font-weight: 600; line-height: 1.3;")
        v_metrics.addWidget(self.lbl_before_metric)

        self.lbl_after_metric = QLabel()
        self.lbl_after_metric.setWordWrap(True)
        self.lbl_after_metric.setStyleSheet(f"color: {LIME}; font-size: 12px; font-weight: 600; line-height: 1.3;")
        v_metrics.addWidget(self.lbl_after_metric)
        self.left_layout.addWidget(self.frame_metrics)

        # Caja de Alerta / Consejo
        self.frame_alert = QFrame()
        self.frame_alert.setStyleSheet("background: #172a38; border-left: 3px solid #5dd8f0; border-radius: 4px; padding: 10px;")
        v_alert = QVBoxLayout(self.frame_alert)
        v_alert.setContentsMargins(6, 6, 6, 6)
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

    def _precompute_simulations(self):
        """Precalcula las simulaciones didácticas una sola vez para respuesta instantánea a 60 fps."""
        for key, info in TOPICS.items():
            b_res = simulate(info["before_gains"])
            a_res = simulate(info["after_gains"])
            self.presets[key] = (b_res, a_res)

    def select_tab(self, key: str):
        if key not in TOPICS:
            key = "iae"
        info = TOPICS[key]

        # Resaltar botón de pestaña activo
        for k, btn in self.tab_buttons.items():
            if k == key:
                btn.setStyleSheet("background: #1c364e; border: 1.5px solid #5dd8f0; color: #5dd8f0; font-weight: 700; border-radius: 6px;")
            else:
                btn.setStyleSheet("background: #13273a; border: 1px solid #28445c; color: #e4f2f8; font-weight: 600; border-radius: 6px;")

        # Actualizar textos
        self.lbl_topic_title.setText(info["title"])
        self.lbl_topic_sub.setText(info["subtitle"])
        self.lbl_concept.setText(info["concept"])

        # Actualizar métricas antes vs después
        b_res, a_res = self.presets[key]
        b_g = info["before_gains"]
        a_g = info["after_gains"]
        b_state = "Caída registrada" if b_res.fallen else f"Ángulo final {math.degrees(b_res.samples[-1].angle):.1f}°"
        a_state = "Estable dentro de ±5°" if a_res.success else "No clasifica"

        self.lbl_before_metric.setText(
            f"🔴 {info['before_label']}\n"
            f"   Gains: Kp={b_g.kp:.2f}, Ki={b_g.ki:.2f}, Kd={b_g.kd:.2f}\n"
            f"   Resultado: IAE = {b_res.iae:.1f} pts  ·  {b_state}\n"
            f"   Diagnóstico: {info['before_desc']}"
        )

        self.lbl_after_metric.setText(
            f"🟢 {info['after_label']}\n"
            f"   Gains: Kp={a_g.kp:.2f}, Ki={a_g.ki:.2f}, Kd={a_g.kd:.2f}\n"
            f"   Resultado: IAE = {a_res.iae:.1f} pts  ·  {a_state}\n"
            f"   Diagnóstico: {info['after_desc']}"
        )

        self.lbl_alert.setText(info["alert"])

        # Renderizar en el gráfico interactivo
        self.chart_view.render_scenario(info, b_res, a_res)
