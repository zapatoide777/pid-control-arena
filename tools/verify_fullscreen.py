from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from pid_game.ui import MainWindow, configure_app
from pid_game.simulation import DURATION
from pid_game.storage import CHALLENGE
import pid_game.motion as motion
import pid_game.visuals as visuals

# Opción exclusiva del capturador: permite inspeccionar el fotograma animado
# en equipos cuyo sistema tiene activada la preferencia de movimiento reducido.
full_motion_preview = '--full-motion-preview' in sys.argv[1:]
if full_motion_preview:
    sys.argv.remove('--full-motion-preview')
    motion.reduced_motion = lambda: False
    visuals.reduced_motion = lambda: False

out = Path('artifacts/pantalla-completa')
out.mkdir(parents=True, exist_ok=True)
app = QApplication.instance() or QApplication(sys.argv)
configure_app(app)
data = out / 'ranking-qa.json'
data.write_text(json.dumps({'schema': 2, 'challenge': CHALLENGE, 'records': []}), encoding='utf-8')
window = MainWindow(data)
window.setWindowTitle('PID - revisión visual')
window.showFullScreen()
QTest.qWait(200)
window.timer.stop()

def capture(name):
    app.processEvents()
    QTest.qWait(200)
    target = out / (name + '.png')
    window.grab().save(str(target))
    print(name, window.size().width(), window.size().height(), window.isFullScreen(), target)

def wait_guide(key):
    deadline = time.monotonic() + 30
    while key not in window.guide_page.presets and time.monotonic() < deadline:
        QTest.qWait(50)
    if key not in window.guide_page.presets:
        raise RuntimeError(f'No se pudo cargar la guía: {key}')

def finish_run(transition_name=None):
    window._render_sample(round(DURATION*1000))
    window._complete_playback()
    if window.stack.currentIndex() == 3:
        if full_motion_preview and transition_name:
            QTest.qWait(350)
            capture(transition_name)
        window.report_animation.setCurrentTime(window.report_animation.duration())
        window.report_sweep.animation.setCurrentTime(window.report_sweep.animation.duration())
        app.processEvents()

def next_attempt():
    window.report_ready_at -= 5
    window.game.ready_at -= 5
    window.tick()
    window.continue_trial()

capture('inicio')
window.open_guide('iae')
wait_guide('iae')
capture('guia_iae')
window.open_guide('kp')
wait_guide('kp')
capture('guia_kp')
window.open_guide('ki')
wait_guide('ki')
capture('guia_ki')
window.open_guide('kd')
wait_guide('kd')
capture('guia_kd')
window.close_guide()
window.start_game()
window._render_sample(2410)
capture('demo')
finish_run()
capture('ajuste')
window.run_trial()
finish_run('pista-animacion')
capture('pista')
next_attempt()
for control, value in zip(window.gain_controls, (2.0, 1.0, 0.5)):
    control.spin.setValue(value)
window.run_trial()
window._render_sample(6000)
capture('seguimiento')
finish_run()
capture('estable')
next_attempt()
window.run_trial()
finish_run()
capture('final')
next_attempt()
capture('ranking')
window.close()
