"""Tres estados públicos; las fases de la partida viven dentro de JUGANDO."""
from enum import Enum
from uuid import uuid4
from .controller import Gains, DEMO_GAINS
from .simulation import Result, simulate


class State(Enum):
    WAITING = "En espera"
    PLAYING = "Jugando"
    FINISHED = "Juego terminado"


class Phase(Enum):
    DEMO = "Demostración"
    EDITING = "Ajustar PID"
    RUNNING = "Prueba en curso"
    FEEDBACK = "Resultado del intento"


class Game:
    def __init__(self):
        self.state = State.WAITING
        self.phase = Phase.DEMO
        self.demo_seen = False
        self.attempts: list[Result] = []
        self.alias = ""
        self.gains = DEMO_GAINS
        self.ready_at = 0.0
        self.record_id = ""

    def begin(self, alias: str):
        if self.state is State.PLAYING:
            raise RuntimeError("Ya hay una partida en curso.")
        self.alias = alias.strip()[:32] or "Jugador"
        self.record_id = str(uuid4())
        self.attempts.clear()
        self.gains = DEMO_GAINS
        self.ready_at = 0.0
        self.state, self.phase = State.PLAYING, Phase.DEMO

    def complete_demo(self, *, skipped: bool = False):
        if self.state is not State.PLAYING or self.phase is not Phase.DEMO:
            raise RuntimeError("No hay demostración activa.")
        if skipped and not self.demo_seen:
            raise RuntimeError("Primero debes ver una demostración completa.")
        self.demo_seen = True
        self.phase = Phase.EDITING

    def launch(self, gains: Gains) -> Result:
        if self.state is not State.PLAYING or self.phase is not Phase.EDITING:
            raise RuntimeError("No puedes ejecutar una prueba en esta fase.")
        if len(self.attempts) >= 3:
            raise RuntimeError("No quedan intentos.")
        self.gains = gains
        result = simulate(gains)
        self.attempts.append(result)
        self.phase = Phase.RUNNING
        return result

    def finish_playback(self, now: float):
        if self.state is not State.PLAYING or self.phase is not Phase.RUNNING:
            raise RuntimeError("No hay prueba ejecutándose.")
        if len(self.attempts) == 3:
            self.state = State.FINISHED
        else:
            self.phase = Phase.FEEDBACK
            self.ready_at = now + (0 if self.attempts[-1].success else 3.0)

    def continue_editing(self, now: float):
        if (self.state is not State.PLAYING or self.phase is not Phase.FEEDBACK
                or now < self.ready_at):
            raise RuntimeError("Todavía no puedes continuar.")
        self.phase = Phase.EDITING

    @property
    def final(self) -> Result:
        if self.state is not State.FINISHED:
            raise RuntimeError("La partida no ha terminado.")
        # min conserva la primera posición cuando hay empate de IAE.
        return min(self.attempts, key=lambda result: result.iae)

    def reset(self):
        if self.state is State.PLAYING:
            raise RuntimeError("La partida sigue en curso.")
        self.state = State.WAITING
