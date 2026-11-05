import json
import math

import pytest

from PySide6.QtCore import Qt, QPoint, QEvent, QAbstractAnimation
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QLabel
from PySide6.QtTest import QTest

from pid_game.game import State, Phase
from pid_game.ui import MainWindow
from pid_game.storage import Ranking, CHALLENGE
from pid_game.simulation import DURATION, hint
from pid_game.visuals import pendulum_radius
from .test_storage import completed_game


def click(widget):
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton)


def end_playback(window):
    window._render_sample(round(DURATION*1000))
    window._complete_playback()


def release_report(window):
    window.game.ready_at -= 4
    window.report_ready_at -= 4
    window.tick()
    click(window.continue_button)


def test_full_ui_flow_controls_hints_final_and_restart(qapp, tmp_path):
    window = MainWindow(tmp_path / "ranking.json")
    window.show()
    qapp.processEvents()
    window.alias_edit.setText("Ensayo <b>literal</b>")
    click(window.start_button)
    assert window.stack.currentIndex() == 1
    assert not any(child.text() == "EN ESPERA" for child in window.findChildren(QLabel))
    assert window.game.attempts == []
    assert not window.run_button.isEnabled()
    assert not window.skip_button.isVisible()
    end_playback(window)
    assert window.game.phase is Phase.EDITING
    assert window.run_button.isEnabled()
    for control, value in zip(window.gain_controls, (2, 1, .5)):
        control.spin.setValue(value)
        assert control.slider.value() == round(value*100)
        editor = control.spin.lineEdit()
        assert editor.width() > 65  # regresión: NoButtons + QSS colapsaba a 1 px
        assert editor.height() >= editor.fontMetrics().height()
    click(window.run_button)
    assert not window.gain_controls[0].isEnabled()
    end_playback(window)
    assert window.game.attempts[-1].success
    assert hint(window.game.attempts[-1]) == ""
    assert window.stack.currentIndex() == 3
    assert window.report_iae.text() == f"{window.game.attempts[-1].iae:.2f}"
    release_report(window)
    assert window.gain_controls[0].spin.value() == 2
    for control, value in zip(window.gain_controls, (.1, 0, 0)):
        control.spin.setValue(value)
    click(window.run_button)
    end_playback(window)
    assert not window.game.attempts[-1].success
    assert not window.continue_button.isEnabled()
    assert window.feedback_label.text() == hint(window.game.attempts[-1])
    # El event loop sigue vivo durante la espera.
    QTest.qWait(50)
    assert window.continue_button.isVisible()
    release_report(window)
    click(window.run_button)
    end_playback(window)
    assert window.game.state is State.FINISHED and window.stack.currentIndex() == 3
    assert window.feedback_label.text() == hint(window.game.attempts[-1])
    release_report(window)
    assert window.stack.currentIndex() == 2
    assert len(Ranking(tmp_path / "ranking.json").records) == 1
    assert window.table.rowCount() == 1
    assert "(actual)" in window.table.item(0, 1).text()
    click(window.new_button)
    click(window.start_button)
    assert window.skip_button.isVisible()
    click(window.skip_button)
    assert window.game.attempts == [] and window.game.phase is Phase.EDITING
    assert not window.playback_active
    window.close()


def test_real_time_demo_uses_timer_and_no_attempt(qapp, tmp_path):
    window = MainWindow(tmp_path / "ranking.json")
    window.show()
    window.speed_combo.setCurrentIndex(0)
    click(window.start_button)
    QTest.qWait(150)
    assert window.progress.value() == 0  # preparación explícita del empujón
    QTest.qWait(750)
    assert 0 < window.progress.value() < 1000
    QTest.qWait(round(DURATION*1000)+900)
    assert not window.playback_active
    assert window.progress.value() == round(DURATION*1000)
    assert window.game.demo_seen and window.game.attempts == []
    assert window.response_chart.response.count() > 500
    window.close()


def test_current_outside_top_ten_table_and_chart(qapp, tmp_path):
    path = tmp_path / "ranking.json"
    ranking = Ranking(path)
    template = ranking.add_game(completed_game("Base"))
    records = [dict(template, id=f"historic-{i}", alias=f"Jugador {i}", iae=float(i+1))
               for i in range(12)]
    path.write_text(json.dumps({"schema": 2, "challenge": CHALLENGE, "records": records}), encoding="utf-8")
    window = MainWindow(path)
    window.game = completed_game("Actual")
    window.show_results()
    window.show()
    qapp.processEvents()
    assert window.table.rowCount() == 11
    assert window.table.item(10, 0).text() == "13"
    assert window.table.item(10, 1).text() == "(actual) Actual"
    chart = window.ranking_chart.chart()
    assert chart.series()[0].barSets()[1].count() == 11
    assert chart.axes(Qt.Orientation.Vertical)[0].titleText() == "log₁₀(1 + IAE)"
    assert chart.series()[0].barSets()[1].at(10) == pytest.approx(math.log10(1 + window.game.final.iae))
    assert "puesto 13" in window.final_metric.text()
    window.resize(1120, 800)
    QTest.qWait(30)
    rect = window.table.visualItemRect(window.table.item(10, 1))
    assert window.table.viewport().rect().intersects(rect)
    window.close()


def test_hint_is_visible_without_scroll_at_minimum_size(qapp, tmp_path):
    window = MainWindow(tmp_path / "ranking.json")
    window.resize(1120, 800)
    window.show()
    window.start_game()
    end_playback(window)
    window.gain_controls[1].spin.setValue(1)
    window.run_trial()
    end_playback(window)
    QTest.qWait(50)
    text = window.feedback_label
    assert not hasattr(window, "feedback_scroll")
    assert text.wordWrap()
    assert text.text() == hint(window.game.attempts[-1])
    assert text.geometry().bottom() < window.report_gains.geometry().top()
    assert window.continue_button.isVisible()
    window.close()


def test_pendulum_length_and_full_range_pause_preserve_physics(qapp, tmp_path):
    base_length = pendulum_radius(246, 300)
    game_length = pendulum_radius(246, 300, 1.4)
    assert game_length >= base_length*1.25

    class Clock:
        ms = 0
        def start(self):
            self.ms = 0
        def elapsed(self):
            return self.ms

    window = MainWindow(tmp_path / "ranking.json")
    window.playback_clock = clock = Clock()
    window.resize(1120, 800)
    window.show()
    window.start_game()
    qapp.processEvents()
    assert window.pendulum.length_scale == 1.4
    scene_bottom = window.pendulum.mapTo(window, QPoint(0, window.pendulum.height())).y()
    metric_top = window.angle_label.mapTo(window, QPoint(0, 0)).y()
    assert scene_bottom <= metric_top
    assert window.playback_rate == 1.0
    clock.ms = 1650  # 0.65 s preparación + 1 s reproducción = 1 s físico
    window.tick()
    assert window.progress.value() == 1000
    window.toggle_pause()
    clock.ms += 4000
    window.tick()
    assert window.progress.value() == 1000
    window.toggle_pause()
    window.tick()
    assert window.progress.value() == 1000
    chart = window.response_chart
    assert chart.view.height() >= 260
    assert not hasattr(chart, "overview")
    assert not hasattr(chart, "zoom_button")
    assert chart.y.max() >= 100  # recorrido global, incluye la caída de la demo
    assert chart.y.min() <= -20
    assert chart.reference.at(0).y() == chart.reference.at(1).y() == 0
    assert chart.reference.at(2).y() == chart.reference.at(3).y() == 45
    original = window.active_result.iae
    clock.ms = round((.65+DURATION/1.0)*1000)+4000
    window.tick()
    assert window.game.demo_seen
    assert window.active_result.iae == original
    assert window.game.attempts == []
    window.close()


def test_gain_keyboard_entry_commits_to_trial(qapp, tmp_path):
    window = MainWindow(tmp_path / "ranking.json")
    window.show()
    window.start_game()
    end_playback(window)
    window.activateWindow()
    qapp.processEvents()
    for control, text, expected in zip(window.gain_controls, ("1.23", "0.45", "0.67"), (1.23, .45, .67)):
        editor = control.spin.lineEdit()
        editor.setFocus()
        qapp.processEvents()
        editor.selectAll()
        text = text.replace(".", control.spin.locale().decimalPoint())
        QTest.keyClicks(editor, text)
        QTest.keyClick(editor, Qt.Key.Key_Tab)
        assert control.spin.value() == pytest.approx(expected)
        assert control.slider.value() == round(expected * 100)
    click(window.run_button)
    assert window.active_result.gains.kp == pytest.approx(1.23)
    assert window.active_result.gains.ki == pytest.approx(.45)
    assert window.active_result.gains.kd == pytest.approx(.67)
    window.close()


@pytest.mark.parametrize("size", [(1120, 800), (1400, 940), (1920, 1000)])
def test_telemetry_has_separate_space_during_fall(qapp, tmp_path, size):
    window = MainWindow(tmp_path / "ranking.json")
    window.resize(*size)
    window.show()
    window.start_game()
    window.timer.stop()
    window._render_sample(2410)
    qapp.processEvents()
    def bounds(widget):
        top = widget.mapTo(window, QPoint(0, 0))
        return top.x(), top.y(), top.x() + widget.width(), top.y() + widget.height()
    scene = bounds(window.pendulum)
    for caption, metric in ((window.angle_caption, window.angle_label),
                            (window.time_caption, window.time_label)):
        title, value = bounds(caption), bounds(metric)
        assert scene[3] <= title[1] <= title[3] <= value[1]
        assert metric.fontMetrics().horizontalAdvance(metric.text()) <= metric.width()
    assert bounds(window.angle_label)[2] <= bounds(window.time_label)[0]
    assert bounds(window.error_label)[1] > max(bounds(window.angle_label)[3], bounds(window.time_label)[3])
    assert window.error_label.fontMetrics().horizontalAdvance(window.error_label.text()) <= window.error_label.width()
    assert window.time_label.text() == "2.41 s"
    window.close()


def test_button_animation_keeps_mouse_keyboard_and_disabled_behavior(qapp):
    from pid_game.motion import ArcadeButton
    button = ArcadeButton("Probar")
    activated = []
    button.clicked.connect(lambda: activated.append(True))
    button.show()
    button.activateWindow()
    qapp.processEvents()
    QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))
    button.hover_animation.pause()
    button.hover_animation.setCurrentTime(button.hover_animation.duration())
    assert button.hoverLevel == pytest.approx(1)
    QTest.mousePress(button, Qt.MouseButton.LeftButton)
    button.press_animation.pause()
    button.press_animation.setCurrentTime(button.press_animation.duration())
    assert button.pressLevel == pytest.approx(1)
    QTest.mouseRelease(button, Qt.MouseButton.LeftButton)
    assert len(activated) == 1
    button.setFocus()
    QTest.keyClick(button, Qt.Key.Key_Space)
    assert len(activated) == 2
    button.setEnabled(False)
    assert button.hoverLevel == 0 and button.pressLevel == 0
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert len(activated) == 2
    button.close()


@pytest.mark.parametrize("reduced", [True, False])
def test_report_motion_preference_preserves_result_and_wait(qapp, tmp_path, monkeypatch, reduced):
    # Cubre ambos caminos independientemente de la preferencia del equipo de QA.
    import pid_game.motion as motion
    import pid_game.visuals as visuals
    monkeypatch.setattr(motion, "reduced_motion", lambda: reduced)
    monkeypatch.setattr(visuals, "reduced_motion", lambda: reduced)
    window = MainWindow(tmp_path / "ranking.json")
    window.show()
    window.start_game()
    end_playback(window)
    window.run_trial()
    end_playback(window)
    window.timer.stop()
    final = window.game.attempts[-1]
    original_iae = window.report_iae.text()
    assert original_iae == f"{final.iae:.2f}"
    assert window.feedback_label.text() == hint(final)
    assert not window.continue_button.isEnabled()
    if reduced:
        assert window.report_animation.state() == QAbstractAnimation.State.Stopped
        assert window.report_score_effect.opacity() == pytest.approx(1)
        assert window.report_hint_effect.opacity() == pytest.approx(1)
        assert window.report_sweep.progress == pytest.approx(1)
        assert window.feedback_label.text()
        window.close()
        return
    window.report_animation.pause()
    window.report_sweep.animation.pause()
    window.report_animation.setCurrentTime(0)
    window.report_sweep.animation.setCurrentTime(0)
    assert window.report_hint_effect.opacity() == pytest.approx(.12)
    window.report_animation.setCurrentTime(350)
    window.report_sweep.animation.setCurrentTime(350)
    assert window.report_score_effect.opacity() > window.report_hint_effect.opacity()
    assert 0 < window.report_sweep.progress < 1
    window.report_animation.setCurrentTime(window.report_animation.duration())
    window.report_sweep.animation.setCurrentTime(window.report_sweep.animation.duration())
    assert window.report_hint_effect.opacity() == pytest.approx(1)
    assert window.report_score_effect.opacity() == pytest.approx(1)
    assert window.report_iae.text() == original_iae and window.game.attempts[-1] is final
    assert not window.continue_button.isEnabled()
    window.close()


def test_default_playback_rates(qapp, tmp_path):
    window = MainWindow(tmp_path / "ranking.json")
    assert [window.speed_combo.itemData(i) for i in range(window.speed_combo.count())] == [1.0, .5]
    assert window.speed_combo.currentData() == 1.0
    window.close()


def test_maximized_report_and_hint_do_not_overlap(qapp, tmp_path, monkeypatch):
    # This test exercises animation frames; make it independent of the OS
    # reduced-motion setting, which is covered by the dedicated motion tests.
    from pid_game import visuals
    monkeypatch.setattr(visuals, "reduced_motion", lambda: False)
    window = MainWindow(tmp_path / "ranking.json")
    window.showMaximized()
    QTest.qWait(80)
    window.start_game()
    window.timer.stop()
    end_playback(window)
    window.run_trial()
    end_playback(window)
    window.report_animation.setCurrentTime(window.report_animation.duration())
    QTest.qWait(80)
    assert window.isMaximized()
    assert not hasattr(window, "feedback_scroll")
    assert window.feedback_label.wordWrap()
    assert window.feedback_label.geometry().bottom() < window.report_gains.geometry().top()
    window.report_strip.animation.pause()
    window.report_strip.animation.setCurrentTime(0)
    assert window.report_strip.reveal == pytest.approx(0)
    window.report_strip.animation.setCurrentTime(window.report_strip.animation.duration())
    assert window.report_strip.reveal == pytest.approx(1)
    assert window.feedback_label.heightForWidth(window.feedback_label.width()) <= window.feedback_label.height()
    for widget in (window.report_title, window.report_gains, window.analysis_progress, window.continue_button):
        position = widget.mapTo(window, QPoint(0, 0))
        assert position.y() >= 0 and position.y() + widget.height() <= window.height()
    window.close()
