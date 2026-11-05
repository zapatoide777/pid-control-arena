from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Gains:
    kp: float = 0.6
    ki: float = 0.02
    kd: float = 0.08

    def __post_init__(self):
        for value, limit in zip((self.kp, self.ki, self.kd), (10, 5, 3)):
            if not math.isfinite(value) or not 0 <= value <= limit:
                raise ValueError("Ganancia fuera de rango.")


DEMO_GAINS = Gains()


class PID:
    """PID paralelo con derivada medida, filtro y anti-windup condicional.

    Se mide velocidad angular en esta simulación ideal sin ruido. La derivada
    filtrada es -ω, sin derivar la referencia ni producir patada derivativa.
    """

    def __init__(self, gains: Gains, limit: float = 2.0, filter_time: float = 0.02):
        self.gains = gains
        self.limit = limit
        self.filter_time = filter_time
        self.integral = 0.0  # contribución integral en N·m
        self.filtered_velocity = 0.0
        self.saturated = False
        self.raw_output = 0.0
        self.output = 0.0

    def command(self, angle: float, velocity: float, dt: float, reference: float = 0.0) -> float:
        self.filtered_velocity += (1 - math.exp(-dt / self.filter_time)) * (
            velocity - self.filtered_velocity)
        error = reference - angle
        increment = self.gains.ki * error * dt
        base = self.gains.kp * error - self.gains.kd * self.filtered_velocity
        candidate = base + self.integral + increment
        # No integrar en dirección que empuje más hacia la saturación.
        if not ((candidate > self.limit and increment > 0) or
                (candidate < -self.limit and increment < 0)):
            self.integral += increment
        raw = base + self.integral
        self.saturated = abs(raw) > self.limit
        self.raw_output = raw
        self.output = max(-self.limit, min(self.limit, raw))
        return self.output
