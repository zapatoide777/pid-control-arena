from dataclasses import dataclass
import math
from .controller import Gains, PID
from .physics import Plant
from .actuator import DCMotor

"""Desafío de 15 s; la reproducción visual no altera el horizonte físico."""
DURATION = 15.0
DT = 0.001
BAND = 5.0
STABILITY_WINDOW = 1.0
STABLE_FROM = DURATION - STABILITY_WINDOW
STEP_TIME = 5.0
STEP_DEGREES = 8.0

# Ventana 1: estabilización tras perturbación inicial [4, 5] s
W1_START = STEP_TIME - STABILITY_WINDOW
W1_END = STEP_TIME
# Ventana 2: estabilización tras escalón de referencia [14, 15] s
W2_START = DURATION - STABILITY_WINDOW
W2_END = DURATION

def reference_at(time: float) -> float:
    return math.radians(STEP_DEGREES) if time >= STEP_TIME else 0.0

INITIAL_VELOCITY = 2.0  # rad/s; perturbación idéntica en demo e intentos


@dataclass(frozen=True)
class Sample:
    time: float
    angle: float  # radianes, sin envolver
    velocity: float
    torque: float
    reference: float = 0.0  # rad; valor posterior al salto si time == STEP_TIME
    current: float = 0.0  # A
    voltage: float = 0.0  # V


@dataclass(frozen=True)
class Result:
    gains: Gains
    samples: tuple[Sample, ...]
    iae: float  # grados segundo
    success: bool
    fallen: bool
    saturation_fraction: float

    @property
    def peak_degrees(self) -> float:
        return max(abs(math.degrees(s.angle)) for s in self.samples)


def iae_segment(a: Sample, b: Sample) -> float:
    """Trapecio del error, usando la referencia válida antes del extremo derecho."""
    return ((b.time-a.time) * (abs(math.degrees(a.angle-a.reference)) +
            abs(math.degrees(b.angle-a.reference))) / 2)


def evaluate(samples: tuple[Sample, ...]) -> tuple[float, bool, bool]:
    iae = sum(iae_segment(a, b) for a, b in zip(samples, samples[1:]))
    fallen = any(abs(s.angle) >= math.pi / 2 for s in samples)
    # Doble ventana de estabilidad: [4, 5] s para el empujón inicial y [14, 15] s para el escalón
    w1 = [s for s in samples if W1_START - 1e-10 <= s.time <= W1_END - 1e-10]
    w2 = [s for s in samples if W2_START - 1e-10 <= s.time <= W2_END + 1e-10]
    stable_w1 = bool(w1) and all(abs(math.degrees(s.angle-s.reference)) <= BAND for s in w1)
    stable_w2 = bool(w2) and all(abs(math.degrees(s.angle-s.reference)) <= BAND for s in w2)
    stable = stable_w1 and stable_w2
    return iae, stable and not fallen, fallen


def simulate(gains: Gains, dt: float = DT, plant: Plant | None = None) -> Result:
    if not math.isfinite(dt) or dt <= 0 or abs(round(DURATION / dt)*dt-DURATION) > 1e-9 or abs(round(STEP_TIME / dt)*dt-STEP_TIME) > 1e-9:
        raise ValueError(f"El paso debe dividir exactamente {DURATION:g} y {STEP_TIME:g} segundos.")
    plant = plant or Plant()
    pid = PID(gains)
    actuator = DCMotor()
    angle, velocity, current = 0.0, INITIAL_VELOCITY, 0.0
    samples = [Sample(0.0, angle, velocity, 0.0)]
    saturated_steps = 0
    steps = round(DURATION / dt)
    for i in range(steps):
        torque = pid.command(angle, velocity, dt, reference_at(i*dt))
        saturated_steps += int(pid.saturated)
        voltage = actuator.voltage(torque)
        angle, velocity, current = actuator.step(plant, angle, velocity, current, voltage, dt)
        samples.append(Sample((i+1)*dt, angle, velocity, actuator.torque_constant*current, reference_at((i+1)*dt), current, voltage))
    values = tuple(samples)
    iae, success, fallen = evaluate(values)
    return Result(gains, values, iae, success, fallen, saturated_steps / steps)


def hint(result: Result) -> str:
    if result.success:
        return ""
    tail = [math.degrees(s.angle-s.reference) for s in result.samples if s.time >= 1.0]
    crossings = sum(a*b < 0 for a, b in zip(tail, tail[1:]))
    if crossings >= 2:
        return "Oscila mucho: sube Kd poco a poco o baja Kp o Ki."
    if result.saturation_fraction > 0.05:
        return "El torque llegó al límite: baja las ganancias más altas."
    if result.fallen:
        return "El péndulo cayó: sube Kp poco a poco y ajusta Kd."
    if abs(tail[-1]) > max(5, abs(tail[0])*1.5):
        return "El error aumenta: sube Kp poco a poco y ajusta Kd."
    return "No se estabilizó: ajusta Kp y Kd, y cambia Ki con cuidado."
