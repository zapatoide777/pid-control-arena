from dataclasses import dataclass
import math
from .controller import Gains, PID
from .physics import Plant
from .actuator import DCMotor
from .textos import text

"""Desafío de 15 s; la reproducción visual no altera el horizonte físico."""
DURATION = 15.0
DT = 0.001
BAND = 5.0
STABILITY_WINDOW = 1.0
STABLE_FROM = DURATION - STABILITY_WINDOW
STEP_TIME = 5.0
STEP_DEGREES = 45.0

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
    pid_torque_raw: float = 0.0  # N·m antes del límite del PID
    pid_torque: float = 0.0  # N·m después del límite del PID
    pid_saturated: bool = False
    current_saturated: bool = False
    integral: float = 0.0  # contribución integral en N·m


@dataclass(frozen=True)
class ResponseMetrics:
    post_step_crossings: int
    overshoot_degrees: float
    settling_time: float | None  # segundos desde STEP_TIME; None si no asienta


def response_metrics(samples: tuple[Sample, ...], step_time: float = STEP_TIME,
                     band: float = BAND, hysteresis_degrees: float = 1.0) -> ResponseMetrics:
    """Calcula métricas de respuesta al escalón desde muestras cronológicas.

    Los cruces comparan ángulo menos referencia, ignorando la zona muerta de
    ±hysteresis_degrees. El asentamiento exige permanecer dentro de ±band hasta
    la última muestra disponible.
    """
    tail = [sample for sample in samples if sample.time >= step_time]
    if not tail:
        return ResponseMetrics(0, 0.0, None)

    errors = [math.degrees(sample.angle - sample.reference) for sample in tail]
    crossings = 0
    side = 0
    for error in errors:
        if error >= hysteresis_degrees:
            new_side = 1
        elif error <= -hysteresis_degrees:
            new_side = -1
        else:
            continue
        if side and side != new_side:
            crossings += 1
        side = new_side

    overshoot = max(0.0, max(errors))
    settling_sample = None
    suffix_stays_in_band = True
    for sample, error in zip(reversed(tail), reversed(errors)):
        if abs(error) <= band + 1e-9 and suffix_stays_in_band:
            settling_sample = sample
        else:
            suffix_stays_in_band = False
    settling_time = (settling_sample.time - step_time
                    if settling_sample is not None else None)
    return ResponseMetrics(crossings, overshoot, settling_time)


@dataclass(frozen=True)
class Result:
    gains: Gains
    samples: tuple[Sample, ...]
    iae: float  # grados segundo
    success: bool
    saturation_fraction: float
    current_saturation_fraction: float = 0.0
    max_current: float = 0.0
    min_integral: float = 0.0
    max_integral: float = 0.0
    post_step_crossings: int = 0
    overshoot_degrees: float = 0.0
    settling_time: float | None = None

    @property
    def pid_saturation_fraction(self) -> float:
        """Fracción de muestras saturadas por el PID (alias explícito)."""
        return self.saturation_fraction

    @property
    def peak_degrees(self) -> float:
        return max(abs(math.degrees(s.angle)) for s in self.samples)


def iae_segment(a: Sample, b: Sample) -> float:
    """Trapecio del error, usando la referencia válida antes del extremo derecho."""
    return ((b.time-a.time) * (abs(math.degrees(a.angle-a.reference)) +
            abs(math.degrees(b.angle-a.reference))) / 2)


def evaluate(samples: tuple[Sample, ...]) -> tuple[float, bool]:
    iae = sum(iae_segment(a, b) for a, b in zip(samples, samples[1:]))
    # Doble ventana de estabilidad: [4, 5] s para el empujón inicial y [14, 15] s para el escalón
    w1 = [s for s in samples if W1_START - 1e-10 <= s.time <= W1_END - 1e-10]
    w2 = [s for s in samples if W2_START - 1e-10 <= s.time <= W2_END + 1e-10]
    stable_w1 = bool(w1) and all(abs(math.degrees(s.angle-s.reference)) <= BAND for s in w1)
    stable_w2 = bool(w2) and all(abs(math.degrees(s.angle-s.reference)) <= BAND for s in w2)
    stable = stable_w1 and stable_w2
    return iae, stable


def simulate(gains: Gains, dt: float = DT, plant: Plant | None = None) -> Result:
    if not math.isfinite(dt) or dt <= 0 or abs(round(DURATION / dt)*dt-DURATION) > 1e-9 or abs(round(STEP_TIME / dt)*dt-STEP_TIME) > 1e-9:
        raise ValueError(f"El paso debe dividir exactamente {DURATION:g} y {STEP_TIME:g} segundos.")
    plant = plant or Plant()
    pid = PID(gains)
    actuator = DCMotor()
    angle, velocity, current = 0.0, INITIAL_VELOCITY, 0.0
    samples = [Sample(0.0, angle, velocity, 0.0)]
    saturated_steps = 0
    current_saturated_steps = 0
    steps = round(DURATION / dt)
    for i in range(steps):
        torque = pid.command(angle, velocity, dt, reference_at(i*dt))
        saturated_steps += int(pid.saturated)
        voltage = actuator.voltage(torque)
        angle, velocity, current = actuator.step(plant, angle, velocity, current, voltage, dt)
        current_saturated = abs(current) >= actuator.current_limit - 1e-9
        current_saturated_steps += int(current_saturated)
        samples.append(Sample(
            (i+1)*dt, angle, velocity, actuator.torque_constant*current,
            reference_at((i+1)*dt), current, voltage,
            pid.raw_output, torque, pid.saturated, current_saturated, pid.integral))
    values = tuple(samples)
    iae, success = evaluate(values)
    response = response_metrics(values)
    return Result(
        gains, values, iae, success, saturated_steps / steps,
        current_saturated_steps / steps,
        max(abs(sample.current) for sample in values),
        min(sample.integral for sample in values),
        max(sample.integral for sample in values),
        response.post_step_crossings, response.overshoot_degrees,
        response.settling_time)


def hint(result: Result) -> str:
    if result.success:
        return ""
    tail = [math.degrees(s.angle-s.reference) for s in result.samples if s.time >= 1.0]
    crossings = sum(a*b < 0 for a, b in zip(tail, tail[1:]))
    if crossings >= 2:
        return text("hints.oscillating")
    if result.saturation_fraction > 0.05:
        return text("hints.saturation")
    if abs(tail[-1]) > max(5, abs(tail[0])*1.5):
        return text("hints.growing_error")
    return text("hints.unstable")
