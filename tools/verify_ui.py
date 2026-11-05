"""Genera capturas reproducibles con datos de prueba, sin tocar el ranking real.

Ejecutar desde la raíz: .venv/Scripts/python -m tools.verify_ui
"""
import json
from pathlib import Path
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from pid_game.controller import Gains
from pid_game.simulation import DURATION
from pid_game.storage import CHALLENGE
from pid_game.ui import MainWindow, configure_app


def main():
    output = Path("artifacts/screenshots")
    output.mkdir(parents=True, exist_ok=True)
    data = output / "qa-ranking.json"
    # Solo fixtures de QA en artifacts; nunca data/ranking.json.
    data.write_text(json.dumps({"schema": 2, "challenge": CHALLENGE, "records": []}), encoding="utf-8")
    app = QApplication([])
    configure_app(app)
    window = MainWindow(data)
    window.resize(1400, 940)
    window.show()

    def capture(name):
        if window.stack.currentIndex() == 3:
            window.report_animation.setCurrentTime(window.report_animation.duration())
            window.report_sweep.animation.setCurrentTime(window.report_sweep.animation.duration())
        app.processEvents()
        target = output / name
        assert window.grab().save(str(target))
        print(target.resolve())

    def continue_report():
        window.game.ready_at -= 4
        window.report_ready_at -= 4
        window.tick()
        window.continue_trial()

    capture("01-inicio.png")
    window.alias_edit.setText("Martín")
    window.start_game()
    window.playback_active = False
    window._render_sample(850)
    capture("02-demostracion.png")
    window._render_sample(round(DURATION*1000))
    window._complete_playback()
    window.run_trial()
    window.playback_active = False
    window._render_sample(round(DURATION*1000))
    window._complete_playback()
    capture("03-pista-y-espera.png")
    window.resize(1120, 800)
    capture("09-analisis-compacto.png")
    window.resize(1400, 940)
    continue_report()
    for control, value in zip(window.gain_controls, (2, .2, .4)):
        control.spin.setValue(value)
    window.run_trial()
    window.playback_active = False
    window._render_sample(round(DURATION*.75*1000))
    capture("04-control-estable.png")
    window.resize(1120, 800)
    capture("08-juego-compacto.png")
    window.resize(1400, 940)
    window._render_sample(round(DURATION*1000))
    window._complete_playback()
    continue_report()
    window.run_trial()
    window.playback_active = False
    window._render_sample(round(DURATION*1000))
    window._complete_playback()
    capture("05-analisis-estable.png")
    continue_report()
    capture("05-resultado-estable.png")

    # Ranking con 12 resultados mejores; el actual debe verse en tabla y gráfico.
    template = window.ranking.records[0]
    window.ranking.records = [dict(template, id=f"qa-{i}", alias=f"Estudiante {i+1}", iae=1+i*.5)
                              for i in range(12)]
    window.new_game()
    window.start_game()
    window.skip_demo()
    for i in range(3):
        window.run_trial()
        window.playback_active = False
        window._render_sample(round(DURATION*1000))
        window._complete_playback()
        if i == 2:
            capture("06-analisis-final.png")
        continue_report()
    capture("06-ranking-y-pista-final.png")
    window.resize(1120, 800)
    capture("07-tamano-minimo.png")
    window.close()


if __name__ == "__main__":
    main()
