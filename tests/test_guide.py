import threading
import time
import math

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from pid_game.ui import MainWindow
from pid_game import guide_view
from pid_game.guide_view import EducationalChart, EducationalGuidePage, TOPICS
from pid_game.controller import Gains
from pid_game.simulation import DURATION, DT, STEP_DEGREES, STEP_TIME, Result, Sample
from pid_game.theme import CORAL, CYAN


def wait_for_preset(page, key, timeout=8.0):
    deadline = time.monotonic() + timeout
    while key not in page.presets and time.monotonic() < deadline:
        QTest.qWait(10)
    assert key in page.presets, f"La simulación de {key} no terminó dentro del plazo."


def test_educational_guide_navigation_and_tabs(qapp, tmp_path):
    window = MainWindow(tmp_path / "ranking.json")
    window.resize(1120, 800)
    window.show()
    qapp.processEvents()

    # Verificar que los botones de acceso existen en la pantalla de inicio
    assert hasattr(window, "iae_button")
    assert hasattr(window, "pid_guide_button")
    assert window.stack.currentIndex() == 0

    # Abrir guía en pestaña IAE
    window.open_guide("iae")
    qapp.processEvents()
    assert window.stack.currentIndex() == 4
    assert window.guide_page.lbl_topic_title.text() == TOPICS["iae"]["title"]
    assert window.guide_page.chart_view.mode == "before"
    if "iae" not in window.guide_page.presets:
        assert window.guide_page.lbl_before_metric.text() == "Calculando comparativa…"
    wait_for_preset(window.guide_page, "iae")

    # Conmutar modos de gráfica
    window.guide_page.chart_view.set_mode("before")
    assert window.guide_page.chart_view.mode == "before"
    assert window.guide_page.chart_view.before_series.isVisible()
    assert not window.guide_page.chart_view.after_series.isVisible()
    assert window.guide_page.chart_view.areas["before"][0].isVisible()
    assert not window.guide_page.chart_view.areas["after"][0].isVisible()
    point_counts = (
        window.guide_page.chart_view.before_series.count(),
        window.guide_page.chart_view.after_series.count(),
    )

    window.guide_page.chart_view.set_mode("after")
    assert window.guide_page.chart_view.mode == "after"
    assert not window.guide_page.chart_view.before_series.isVisible()
    assert window.guide_page.chart_view.after_series.isVisible()
    assert not window.guide_page.chart_view.areas["before"][0].isVisible()
    assert window.guide_page.chart_view.areas["after"][0].isVisible()
    window.guide_page.chart_view.set_mode("both")
    assert all(area.isVisible() for area, _, _ in window.guide_page.chart_view.areas.values())
    assert point_counts == (
        window.guide_page.chart_view.before_series.count(),
        window.guide_page.chart_view.after_series.count(),
    )

    chart = window.guide_page.chart_view
    assert chart.y_axis.labelFormat() == "%.0f"
    assert chart.y_axis.titleText() == "Ángulo (grados)"
    assert "ANTES" in chart.legend_label.text()
    assert "DESPUÉS" in chart.legend_label.text()
    assert CORAL in chart.legend_label.text()
    assert CYAN in chart.legend_label.text()
    assert chart.before_series.pen().color().name() == CORAL
    assert chart.after_series.pen().color().name() == CYAN
    assert chart.before_series.count() <= 1805
    assert chart.after_series.count() <= 1805
    assert chart.areas["before"][1].count() <= 245
    assert chart.areas["after"][1].count() <= 245

    before, after = window.guide_page.presets["iae"]
    assert f"IAE = {before.iae:.1f} pts" in window.guide_page.lbl_before_metric.text()
    assert f"IAE = {after.iae:.1f} pts" in window.guide_page.lbl_after_metric.text()

    # Recorrer las demás pestañas (Kp, Ki, Kd)
    for topic in ("kp", "ki", "kd", "iae"):
        window.guide_page.select_tab(topic)
        qapp.processEvents()
        assert window.guide_page.lbl_topic_title.text() == TOPICS[topic]["title"]
        wait_for_preset(window.guide_page, topic)
        before, after = window.guide_page.presets[topic]
        assert f"IAE = {before.iae:.1f} pts" in window.guide_page.lbl_before_metric.text()
        assert f"IAE = {after.iae:.1f} pts" in window.guide_page.lbl_after_metric.text()

    # Probar retorno limpio al menú
    window.close_guide()
    qapp.processEvents()
    assert window.stack.currentIndex() == 0

    # Abrir guía desde botón Kp directo
    window.open_guide("kp")
    qapp.processEvents()
    assert window.stack.currentIndex() == 4
    assert window.guide_page.lbl_topic_title.text() == TOPICS["kp"]["title"]

    window.close_guide()
    assert window.stack.currentIndex() == 0
    window.close()


def test_guide_calculations_run_off_ui_thread_and_tabs_stay_responsive(qapp, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    real_simulate = guide_view.simulate

    def slow_simulation(gains):
        started.set()
        assert release.wait(4)
        return real_simulate(gains)

    monkeypatch.setattr(guide_view, "simulate", slow_simulation)
    page = EducationalGuidePage(on_back=lambda: None)
    page.show()
    assert started.wait(1), "La simulación no se inició en segundo plano."

    start = time.monotonic()
    page.select_tab("kd")
    elapsed = time.monotonic() - start
    assert elapsed < 0.25
    assert page.lbl_topic_title.text() == TOPICS["kd"]["title"]
    assert page.lbl_before_metric.text() == "Calculando comparativa…"

    release.set()
    wait_for_preset(page, "kd")
    assert page.chart_view.before_series.count() > 0
    assert page.chart_view.after_series.count() > 0
    page.close()


def test_chart_limits_qtcharts_geometry_and_preserves_reference_step(qapp):
    samples = tuple(
        Sample(
            time=index * DT,
            angle=math.radians(6 * math.sin(index * DT)),
            velocity=0,
            torque=0,
            reference=math.radians(STEP_DEGREES if index * DT >= STEP_TIME else 0),
        )
        for index in range(round(DURATION / DT) + 1)
    )
    result = Result(Gains(), samples, 0.0, False, 0.0)
    chart = EducationalChart()

    start = time.monotonic()
    chart.render_scenario(TOPICS["iae"], result, result)
    render_time = time.monotonic() - start

    assert render_time < 5.0
    assert chart.before_series.count() <= 1805
    assert chart.after_series.count() <= 1805
    for area, upper, lower in chart.areas.values():
        assert 0 < upper.count() <= 245
        area_times = {round(upper.at(i).x(), 3) for i in range(upper.count())}
        assert STEP_TIME in area_times
