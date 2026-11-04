import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    from pid_game.ui import configure_app
    app = QApplication.instance() or QApplication([])
    configure_app(app)
    yield app
