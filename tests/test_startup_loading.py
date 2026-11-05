import threading
import time

from PySide6.QtTest import QTest

from pid_game import guide_view
from pid_game.game import State
from pid_game.ui import MainWindow
from pid_game.guide_view import EducationalChart, TOPICS
from pid_game.simulation import DURATION, Result, Sample


def wait_for_preload(window, timeout=5.0):
    deadline = time.monotonic() + timeout
    while len(window.guide_page._preload_done) < len(TOPICS) and time.monotonic() < deadline:
        QTest.qWait(10)
    assert len(window.guide_page._preload_done) == len(TOPICS), "La precarga no terminó dentro del plazo."


def test_startup_preloads_all_guide_comparisons_and_keeps_play_available(qapp, tmp_path, monkeypatch):
    computed = []

    def fast_simulation(gains):
        computed.append(gains)
        return sample_result(gains)

    monkeypatch.setattr(guide_view, "simulate", fast_simulation)
    window = MainWindow(tmp_path / "ranking.json")
    progress = []
    window.guide_page.preload_progress.connect(lambda done, total, error: progress.append((done, total, error)))
    window.show()

    wait_for_preload(window)

    assert progress[-1] == (len(TOPICS), len(TOPICS), "")
    assert set(window.guide_page.presets) == set(TOPICS)
    assert len(computed) == 2 * len(TOPICS)
    assert not hasattr(window, "guide_preload_label")
    assert not hasattr(window, "guide_preload_progress")
    assert window.start_button.isEnabled()

    window.start_game()
    assert window.stack.currentIndex() == 1
    assert window.game.phase.value == "Demostración"
    window.close()


def test_preloaded_results_render_only_after_opening_guide(qapp, tmp_path, monkeypatch):
    def fast_simulation(gains):
        return sample_result(gains)

    rendered_topics = []
    real_render = EducationalChart.render_scenario

    def track_render(chart, topic, before, after):
        rendered_topics.append(topic["title"])
        return real_render(chart, topic, before, after)

    monkeypatch.setattr(guide_view, "simulate", fast_simulation)
    monkeypatch.setattr(EducationalChart, "render_scenario", track_render)
    window = MainWindow(tmp_path / "ranking.json")
    window.show()
    wait_for_preload(window)

    assert rendered_topics == []
    window.open_guide("iae")
    qapp.processEvents()
    assert rendered_topics
    assert set(rendered_topics) == {TOPICS["iae"]["title"]}
    window.close()


def test_starting_before_deferred_preload_runs_keeps_game_free_of_guide_work(qapp, tmp_path, monkeypatch):
    calls = []

    def fast_simulation(gains):
        calls.append(gains)
        return sample_result(gains)

    monkeypatch.setattr(guide_view, "simulate", fast_simulation)
    window = MainWindow(tmp_path / "ranking.json")
    window.show()
    window.start_game()
    QTest.qWait(30)

    assert calls == []
    assert not window.guide_page._preloading
    assert window.guide_page._pending_keys == []
    assert window.stack.currentIndex() == 1
    window.close()


def test_startup_preload_reports_failures(qapp, tmp_path, monkeypatch):
    failed_once = False

    def fail_one_simulation(gains):
        nonlocal failed_once
        if not failed_once and gains == TOPICS["iae"]["before_gains"]:
            failed_once = True
            raise RuntimeError("fallo temporal de prueba")
        return sample_result(gains)

    monkeypatch.setattr(guide_view, "simulate", fail_one_simulation)
    window = MainWindow(tmp_path / "ranking.json")
    progress = []
    window.guide_page.preload_progress.connect(lambda done, total, error: progress.append((done, total, error)))
    window.show()
    wait_for_preload(window)

    assert set(window.guide_page.presets) == set(TOPICS) - {"iae"}
    assert progress[-1][:2] == (len(TOPICS), len(TOPICS))
    assert "iae" in progress[-1][2]
    assert "fallo temporal de prueba" in progress[-1][2]

    window.close()


def test_starting_game_pauses_guide_queue_and_new_game_resumes_it(qapp, tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def paused_simulation(gains):
        started.set()
        assert release.wait(4), "La prueba no liberó el cálculo en segundo plano."
        return sample_result(gains)

    monkeypatch.setattr(guide_view, "simulate", paused_simulation)
    window = MainWindow(tmp_path / "ranking.json")
    window.show()
    deadline = time.monotonic() + 1.0
    while not started.is_set() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert started.is_set(), "La precarga no se inició al mostrar la ventana."
    assert len(window.guide_page._pending_keys) == len(TOPICS) - 1

    window.start_game()
    assert window.guide_page._pending_keys == []
    assert not window.guide_page._preloading

    release.set()
    deadline = time.monotonic() + 2.0
    while window.guide_page._running_key is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.guide_page._running_key is None
    assert len(window.guide_page.presets) == 1

    window.game.state = State.FINISHED
    window.new_game()
    wait_for_preload(window)
    assert set(window.guide_page.presets) == set(TOPICS)
    window.close()


def test_closing_window_discards_unstarted_guide_preloads(qapp, tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def paused_simulation(gains):
        started.set()
        assert release.wait(4), "La prueba no liberó el cálculo en segundo plano."
        return sample_result(gains)

    monkeypatch.setattr(guide_view, "simulate", paused_simulation)
    window = MainWindow(tmp_path / "ranking.json")
    window.show()

    deadline = time.monotonic() + 1.0
    while not started.is_set() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert started.is_set(), "La precarga no se inició al mostrar la ventana."
    assert window.start_button.isEnabled()
    assert not window.guide_page.presets
    assert len(window.guide_page._pending_keys) == len(TOPICS) - 1

    window.close()
    assert window.guide_page._pending_keys == []
    release.set()

    deadline = time.monotonic() + 2.0
    while window.guide_page._running_key is not None and time.monotonic() < deadline:
        QTest.qWait(10)
    assert window.guide_page._running_key is None
    assert len(window.guide_page.presets) <= 1


def sample_result(gains):
    samples = (
        Sample(0.0, 0.0, 0.0, 0.0, 0.0),
        Sample(DURATION, 0.0, 0.0, 0.0, 0.0),
    )
    return Result(gains, samples, 0.0, False, 0.0)
