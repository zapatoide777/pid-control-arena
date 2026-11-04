import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from pid_game.ui import MainWindow
from pid_game.guide_view import EducationalGuidePage, TOPICS


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
    assert window.guide_page.chart_view.mode == "both"

    # Conmutar modos de gráfica
    window.guide_page.chart_view.set_mode("before")
    assert window.guide_page.chart_view.mode == "before"
    assert window.guide_page.chart_view.before_series.isVisible()
    assert not window.guide_page.chart_view.after_series.isVisible()

    window.guide_page.chart_view.set_mode("after")
    assert window.guide_page.chart_view.mode == "after"
    assert not window.guide_page.chart_view.before_series.isVisible()
    assert window.guide_page.chart_view.after_series.isVisible()

    # Recorrer las demás pestañas (Kp, Ki, Kd)
    for topic in ("kp", "ki", "kd", "iae"):
        window.guide_page.select_tab(topic)
        qapp.processEvents()
        assert window.guide_page.lbl_topic_title.text() == TOPICS[topic]["title"]

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
