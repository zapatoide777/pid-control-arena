"""Análisis local reproducible del PID digital y de su planta RK4.

No cambia el juego ni sus validaciones. Ejecutar desde el proyecto con:

    python -m tools.analisis_estabilidad

El Jacobiano se construye para la misma actualización exponencial del filtro,
Euler explícito de la integral y paso RK4 del motor/planta usados en
``pid_game.simulation``. El análisis local supone operación lejos de los
límites del PID, tensión y corriente.
"""
from __future__ import annotations

import argparse
import cmath
import csv
import html
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from pid_game.actuator import DCMotor
from pid_game.controller import Gains
from pid_game.physics import Plant
from pid_game.simulation import DT, STEP_DEGREES, STEP_TIME, simulate

try:  # acelerador opcional; el analizador conserva un fallback stdlib completo
    import numpy as _numpy
except ImportError:  # pragma: no cover - depende del runtime disponible
    _numpy = None


@dataclass(frozen=True)
class AnalysisGains:
    """Ganancias sin validación para estudiar umbrales fuera del juego.

    ``Gains`` conserva intactos los límites interactivos del juego. Esta
    estructura mínima permite extender un barrido teórico más allá de ellos.
    """

    kp: float
    ki: float = 0.0
    kd: float = 0.0


@dataclass(frozen=True)
class Equilibrium:
    angle: float
    velocity: float
    current: float
    voltage: float
    torque: float
    integral: float | None
    reference: float
    feasible: bool = True


def _static_torque(plant: Plant, angle: float) -> float:
    """Torque de actuador que equilibra la gravedad a velocidad cero."""
    return -plant.mass * plant.gravity * plant.length * math.sin(angle)


def _p_only_angle(plant: Plant, gains, reference_rad: float) -> float:
    """Equilibrio P-only más cercano al setpoint, con I inactivo."""
    kp = gains.kp
    gravity_moment = plant.mass * plant.gravity * plant.length
    if kp <= 0:
        # Con Kp=0 el setpoint no entra al control; los ceros de sin(theta)
        # son los equilibrios. Escoger el más cercano a la referencia dada.
        return round(reference_rad / math.pi) * math.pi

    def residual(angle: float) -> float:
        # Kp(r-theta) = -mgl sin(theta)
        return kp * (reference_rad - angle) + gravity_moment * math.sin(angle)

    at_reference = residual(reference_rad)
    if abs(at_reference) <= 1e-14:
        return reference_rad

    radius = gravity_moment / kp
    lo, hi = reference_rad - radius - 1e-12, reference_rad + radius + 1e-12
    f_lo, f_hi = residual(lo), residual(hi)
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if f_lo * f_hi > 0:
        # This can only occur through roundoff at a tangential root.
        angle = reference_rad
        for _ in range(100):
            value = residual(angle)
            derivative = -kp + gravity_moment * math.cos(angle)
            if abs(derivative) < 1e-14:
                break
            updated = angle - value / derivative
            if abs(updated - angle) < 1e-14:
                return updated
            angle = updated
        raise ValueError("No se pudo encerrar el equilibrio P-only.")

    # Bisección determinista; para Kp > mgl el equilibrio es único.
    for _ in range(100):
        mid = (lo + hi) / 2
        f_mid = residual(mid)
        if abs(f_mid) < 1e-14 or hi - lo < 1e-14:
            return mid
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def equilibria(plant: Plant, gains, reference_rad: float) -> list[Equilibrium]:
    """Devuelve el equilibrio local de seguimiento para una referencia fija.

    Con Ki>0, el integrador compensa gravedad en ``theta=reference``. Con
    Ki=0, el integrador está ausente y se devuelve el equilibrio P-only más
    cercano al setpoint, incluyendo el sesgo estático que pueda producir.
    """
    if gains.ki > 0:
        angle = reference_rad
        torque = _static_torque(plant, angle)
        integral = torque
    else:
        angle = _p_only_angle(plant, gains, reference_rad)
        torque = gains.kp * (reference_rad - angle)
        integral = None

    motor = DCMotor()
    current = torque / motor.torque_constant
    voltage = motor.resistance * current
    feasible = (abs(torque) <= 2.0 + 1e-12
                and abs(current) <= motor.current_limit + 1e-12
                and abs(voltage) <= motor.voltage_limit + 1e-12)
    return [Equilibrium(angle, 0.0, current, voltage, torque, integral,
                        reference_rad, feasible)]


def _zeros(rows: int, cols: int) -> list[list[float]]:
    return [[0.0 for _ in range(cols)] for _ in range(rows)]


def _matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(len(b)))
             for j in range(len(b[0]))] for i in range(len(a))]


def _rk4_linear_step(matrix: Sequence[Sequence[float]], input_vector: Sequence[float],
                     state: Sequence[float], held_input: float, dt: float) -> list[float]:
    def derivative(x):
        return [sum(matrix[i][j] * x[j] for j in range(len(x)))
                + input_vector[i] * held_input for i in range(len(x))]

    k1 = derivative(state)
    k2 = derivative([x + dt * k / 2 for x, k in zip(state, k1)])
    k3 = derivative([x + dt * k / 2 for x, k in zip(state, k2)])
    k4 = derivative([x + dt * k for x, k in zip(state, k3)])
    return [x + dt * (a + 2*b + 2*c + d) / 6
            for x, a, b, c, d in zip(state, k1, k2, k3, k4)]


def linearized_map(plant: Plant, gains, dt: float, reference_rad: float,
                   equilibrium: Equilibrium | None = None) -> list[list[float]]:
    """Exact Jacobian of one unsaturated digital sample, including RK4.

    State order is ``[theta, omega, current, filtered_velocity]`` and includes
    ``integral`` as the final coordinate only when Ki>0. This is the Jacobian
    of the discrete implementation, not a continuous-time approximation.
    """
    if dt <= 0 or not math.isfinite(dt):
        raise ValueError("dt debe ser positivo y finito.")
    if equilibrium is None:
        equilibrium = equilibria(plant, gains, reference_rad)[0]
    if not equilibrium.feasible:
        raise ValueError("El equilibrio queda fuera de los límites del actuador.")

    motor = DCMotor()
    theta = equilibrium.angle
    # d/domega tanh(omega/vs) at omega=0 is 1/vs.
    effective_damping = plant.damping + plant.coulomb_friction / plant.friction_speed
    continuous_a = [
        [0.0, 1.0, 0.0],
        [plant.mass * plant.gravity * plant.length * math.cos(theta) / plant.inertia,
         -effective_damping / plant.inertia,
         motor.torque_constant / plant.inertia],
        [0.0, -motor.back_emf_constant / motor.inductance,
         -motor.resistance / motor.inductance],
    ]
    # The held input to the actuator is the PID torque q, mapped to voltage
    # with V=R*q/Kt (locally away from the voltage clamp).
    input_q = [0.0, 0.0,
               motor.resistance / (motor.torque_constant * motor.inductance)]

    plant_dim = 3
    plant_map = _zeros(plant_dim, plant_dim)
    input_map = [0.0] * plant_dim
    for column in range(plant_dim):
        basis = [0.0] * plant_dim
        basis[column] = 1.0
        stepped = _rk4_linear_step(continuous_a, input_q, basis, 0.0, dt)
        for row in range(plant_dim):
            plant_map[row][column] = stepped[row]
    input_map = _rk4_linear_step(continuous_a, input_q, [0.0] * plant_dim, 1.0, dt)

    filter_alpha = 1.0 - math.exp(-dt / 0.02)
    integral_active = gains.ki > 0
    dimension = 5 if integral_active else 4
    theta_i, omega_i, current_i, filter_i = range(4)
    integral_i = 4 if integral_active else None

    # Sensitivity of this sample's held torque command to each current state.
    command_sensitivity = [0.0] * dimension
    command_sensitivity[theta_i] = -gains.kp - (gains.ki * dt if integral_active else 0.0)
    command_sensitivity[omega_i] = -gains.kd * filter_alpha
    command_sensitivity[filter_i] = -gains.kd * (1.0 - filter_alpha)
    if integral_active:
        command_sensitivity[integral_i] = 1.0

    result = _zeros(dimension, dimension)
    # Physical plant rows: RK4 map plus the held command sensitivity.
    for row in range(plant_dim):
        for column in range(dimension):
            base = plant_map[row][column] if column < plant_dim else 0.0
            result[row][column] = base + input_map[row] * command_sensitivity[column]

    # Exact exponential velocity-filter update used by PID.command.
    result[filter_i][omega_i] = filter_alpha
    result[filter_i][filter_i] = 1.0 - filter_alpha

    # Euler integral contribution is a state only for Ki>0. When Ki=0, the
    # game's initialized zero integral cannot affect the dynamics and is omitted.
    if integral_active:
        result[integral_i][theta_i] = -gains.ki * dt
        result[integral_i][integral_i] = 1.0
    return result


def _characteristic_coefficients(matrix: Sequence[Sequence[float]]) -> list[float]:
    """Faddeev-LeVerrier coefficients, monic polynomial in descending order."""
    n = len(matrix)
    b = [[float(i == j) for j in range(n)] for i in range(n)]
    coefficients = [1.0]
    for k in range(1, n + 1):
        product = _matmul(matrix, b)
        coefficient = -sum(product[i][i] for i in range(n)) / k
        coefficients.append(coefficient)
        b = [[product[i][j] + (coefficient if i == j else 0.0)
              for j in range(n)] for i in range(n)]
    return coefficients


def _poly_value(coefficients: Sequence[float], z: complex) -> complex:
    value = complex(coefficients[0])
    for coefficient in coefficients[1:]:
        value = value * z + coefficient
    return value


def _polynomial_roots(coefficients: Sequence[float]) -> list[complex]:
    """Durand-Kerner roots for the small (4x4/5x5) real Jacobians here."""
    degree = len(coefficients) - 1
    if degree <= 0:
        return []
    leading = coefficients[0]
    normalized = [coefficient / leading for coefficient in coefficients]
    radius = 1.0 + max(abs(coefficient) for coefficient in normalized[1:])
    # Offset avoids common symmetric starts at a repeated or real root.
    roots = [radius * cmath.exp(2j * math.pi * (i + 0.271828) / degree)
             for i in range(degree)]
    for _ in range(5000):
        old = roots[:]
        max_delta = 0.0
        for i in range(degree):
            denominator = 1 + 0j
            for j in range(degree):
                if i != j:
                    denominator *= old[i] - old[j]
            if abs(denominator) < 1e-28:
                denominator += complex(1e-18, 1e-18)
            delta = _poly_value(normalized, old[i]) / denominator
            roots[i] = old[i] - delta
            max_delta = max(max_delta, abs(delta))
        if max_delta < 2e-13:
            break
    # Nearly-real roots are normalized so reports are readable and stable.
    return [complex(root.real, 0.0) if abs(root.imag) < 2e-11 else root
            for root in roots]


def discrete_poles(plant: Plant, gains, dt: float, reference_rad: float,
                   equilibrium: Equilibrium | None = None) -> list[complex]:
    """Polos del mapa local discreto, ordenados por módulo y fase."""
    matrix = linearized_map(plant, gains, dt, reference_rad, equilibrium)
    if _numpy is not None:
        poles = [complex(value) for value in _numpy.linalg.eigvals(matrix)]
    else:
        poles = _polynomial_roots(_characteristic_coefficients(matrix))
    return sorted(poles, key=lambda root: (abs(root), cmath.phase(root)))


def analytic_p_only_limits(plant: Plant | None = None,
                           motor: DCMotor | None = None) -> dict[str, float]:
    """Límites Routh del modelo continuo lineal, P-only, sin saturación.

    La cota superior es una comparación analítica del modelo idealizado y no
    cambia los límites ``Gains.kp`` del juego.
    """
    plant = plant or Plant()
    motor = motor or DCMotor()
    gravity = plant.mass * plant.gravity * plant.length
    damping = plant.damping + plant.coulomb_friction / plant.friction_speed
    # Characteristic polynomial:
    # J L s^3 + (J R + b_eff L)s^2 +
    # (b_eff R - mgl L + Kt Ke)s + R(Kp - mgl).
    a3 = plant.inertia * motor.inductance
    a2 = plant.inertia * motor.resistance + damping * motor.inductance
    a1 = (damping * motor.resistance - gravity * motor.inductance
          + motor.torque_constant * motor.back_emf_constant)
    lower = gravity
    upper = gravity + a2 * a1 / (a3 * motor.resistance)
    return {"lower_kp": lower, "upper_kp": upper,
            "a3": a3, "a2": a2, "a1": a1,
            "gravity_moment": gravity,
            "effective_damping": damping}


def digital_p_only_upper_boundary(plant: Plant | None = None,
                                  dt: float = DT,
                                  low: float = 10.0,
                                  high: float = 40.0,
                                  iterations: int = 40) -> float:
    """Busca por bisección el cruce superior |z|=1 del mapa discreto P-only.

    Usa ``AnalysisGains`` para explorar fuera del límite de interfaz sin tocar
    ``Gains``. El intervalo entregado debe encerrar una transición estable a
    inestable.
    """
    plant = plant or Plant()

    def stable(kp: float) -> bool:
        gains = AnalysisGains(kp)
        eq = equilibria(plant, gains, 0.0)[0]
        return _spectral_radius(discrete_poles(plant, gains, dt, 0.0, eq)) < 1.0

    if not stable(low) or stable(high):
        raise ValueError("El intervalo no encierra el cruce superior |z|=1.")
    for _ in range(iterations):
        middle = (low + high) / 2
        if stable(middle):
            low = middle
        else:
            high = middle
    return (low + high) / 2


def _spectral_radius(poles: Iterable[complex]) -> float:
    return max((abs(pole) for pole in poles), default=0.0)


def _spectral_bounds(series: Iterable[tuple]) -> tuple[float, float]:
    values = [value for curve in series for _, value in curve[1]]
    if not values:
        return 0.99, 1.01
    low, high = min(min(values), 1.0), max(max(values), 1.0)
    padding = max((high - low) * 0.14, 0.00015)
    return low - padding, high + padding


def _stable_intervals_for_slice(plant: Plant, dt: float, kp_min: float,
                                kp_max: float, ki: float, kd: float,
                                reference_rad: float,
                                kp_step: float = 0.5,
                                refinements: int = 24) -> tuple[list[tuple[float, float]], list[dict]]:
    """Encuentra bandas estables en Kp y refina cruces de |z|=1 por bisección."""
    def stable(kp: float) -> bool:
        gains = AnalysisGains(kp, ki, kd)
        equilibrium = equilibria(plant, gains, reference_rad)[0]
        return _spectral_radius(discrete_poles(
            plant, gains, dt, reference_rad, equilibrium)) < 1.0

    count = round((kp_max - kp_min) / kp_step)
    grid = [kp_min + index * kp_step for index in range(count + 1)]
    if not math.isclose(grid[-1], kp_max, abs_tol=1e-10):
        grid.append(kp_max)
    states = [stable(kp) for kp in grid]
    crossings: list[tuple[float, str]] = []
    for left, right, left_stable, right_stable in zip(grid, grid[1:], states, states[1:]):
        if left_stable == right_stable:
            continue
        lo, hi = left, right
        for _ in range(refinements):
            mid = (lo + hi) / 2
            if stable(mid) == left_stable:
                lo = mid
            else:
                hi = mid
        crossing = (lo + hi) / 2
        direction = "entra" if right_stable else "sale"
        crossings.append((crossing, direction))

    intervals: list[tuple[float, float]] = []
    active = states[0]
    start = kp_min if active else None
    for crossing, direction in crossings:
        if direction == "sale" and active:
            intervals.append((start if start is not None else kp_min, crossing))
            start, active = None, False
        elif direction == "entra" and not active:
            start, active = crossing, True
    if active:
        intervals.append((start if start is not None else kp_min, kp_max))

    boundary_rows = [{"kp_boundary": crossing, "transition": direction}
                     for crossing, direction in crossings]
    return intervals, boundary_rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _svg_chart(path: Path, *, title: str, x_label: str, y_label: str,
               series: list[tuple],
               x_bounds: tuple[float, float], y_bounds: tuple[float, float],
               horizontal: tuple[float, str, str] | None = None,
               verticals: list[tuple] | None = None,
               log_y: bool = False) -> None:
    width, height = 1020, 560
    left, right, top, bottom = 96, 36, 64, 92
    plot_w, plot_h = width - left - right, height - top - bottom
    x0, x1 = x_bounds
    y0, y1 = y_bounds

    def y_transform(value: float) -> float:
        if log_y:
            value = math.log10(max(value, 1e-9))
            low, high = math.log10(y0), math.log10(y1)
        else:
            low, high = y0, y1
        return top + plot_h * (1 - (value - low) / (high - low))

    def px(value: float) -> float:
        return left + plot_w * (value - x0) / (x1 - x0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#f7f9fc"/>',
             f'<text x="{left}" y="34" font-family="Segoe UI,Arial" font-size="23" font-weight="700" fill="#15233d">{html.escape(title)}</text>',
             f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fff" stroke="#cad4e2"/>']
    for tick in range(6):
        ratio = tick / 5
        x_value = x0 + ratio * (x1 - x0)
        x = px(x_value)
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top+plot_h}" stroke="#e7ecf2"/>')
        parts.append(f'<text x="{x:.2f}" y="{top+plot_h+25}" text-anchor="middle" font-family="Segoe UI,Arial" font-size="13" fill="#43536b">{x_value:g}</text>')
        if log_y:
            low_log, high_log = math.log10(y0), math.log10(y1)
            y_value = 10 ** (low_log + ratio * (high_log-low_log))
        else:
            y_value = y0 + (1-ratio) * (y1-y0)
        y = y_transform(y_value)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}" stroke="#e7ecf2"/>')
        label = f"{y_value:.3g}"
        parts.append(f'<text x="{left-12}" y="{y+4:.2f}" text-anchor="end" font-family="Segoe UI,Arial" font-size="13" fill="#43536b">{label}</text>')
    if horizontal:
        value, label, color = horizontal
        y = y_transform(value)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}" stroke="{color}" stroke-width="2" stroke-dasharray="8 6"/>')
        parts.append(f'<text x="{left+plot_w-8}" y="{y-8:.2f}" text-anchor="end" font-family="Segoe UI,Arial" font-size="13" fill="{color}">{html.escape(label)}</text>')
    for marker in verticals or []:
        value, label, color = marker[:3]
        label_offset = marker[3] if len(marker) > 3 else 0
        x = px(value)
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top+plot_h}" stroke="{color}" stroke-width="1.5" stroke-dasharray="5 5"/>')
        parts.append(f'<text x="{x+5:.2f}" y="{top+17+label_offset}" font-family="Segoe UI,Arial" font-size="12" fill="{color}">{html.escape(label)}</text>')
    for curve in series:
        label, points, color = curve[:3]
        dash = curve[3] if len(curve) > 3 else None
        plotted = " ".join(f"{px(x):.2f},{y_transform(y):.2f}" for x, y in points
                            if x0 <= x <= x1 and y0 <= y <= y1)
        if plotted:
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            parts.append(f'<polyline points="{plotted}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"{dash_attr}/>')
        for x, y in points:
            if x0 <= x <= x1 and y0 <= y <= y1:
                parts.append(f'<circle cx="{px(x):.2f}" cy="{y_transform(y):.2f}" r="2.6" fill="{color}"/>')
    parts.append(f'<text x="{left+plot_w/2:.2f}" y="{height-13}" text-anchor="middle" font-family="Segoe UI,Arial" font-size="15" fill="#15233d">{html.escape(x_label)}</text>')
    parts.append(f'<text x="24" y="{top+plot_h/2:.2f}" transform="rotate(-90 24 {top+plot_h/2:.2f})" text-anchor="middle" font-family="Segoe UI,Arial" font-size="15" fill="#15233d">{html.escape(y_label)}</text>')
    legend_x = left + 12
    legend_columns = min(max(len(series), 1), 3)
    for index, curve in enumerate(series):
        label, _, color = curve[:3]
        dash = curve[3] if len(curve) > 3 else None
        x = legend_x + (index % legend_columns) * 290
        y = height - 55 + (index // legend_columns) * 19
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<line x1="{x}" y1="{y}" x2="{x+26}" y2="{y}" stroke="{color}" stroke-width="3"{dash_attr}/>')
        parts.append(f'<text x="{x+34}" y="{y+5}" font-family="Segoe UI,Arial" font-size="12" fill="#43536b">{html.escape(label)}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def run_analysis(output_dir: Path, dt: float = DT) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    plant = Plant()
    zero_ref = 0.0
    step_ref = math.radians(STEP_DEGREES)
    kp_analytic = analytic_p_only_limits(plant)
    kp_digital_upper = digital_p_only_upper_boundary(plant, dt)

    # Local poles for representative controllers at both relevant equilibria.
    cases = [
        ("P puro, demo", AnalysisGains(0.1), zero_ref),
        ("P-D", AnalysisGains(2.0, 0.0, 0.5), zero_ref),
        ("Base juego", Gains(2.0, 1.0, 0.5), zero_ref),
        ("Base juego en 45°", Gains(2.0, 1.0, 0.5), step_ref),
        ("Ganancia alta", Gains(10.0, 5.0, 3.0), zero_ref),
        ("Ganancia alta en 45°", Gains(10.0, 5.0, 3.0), step_ref),
    ]
    local_rows = []
    for label, gains, reference in cases:
        equilibrium = equilibria(plant, gains, reference)[0]
        poles = discrete_poles(plant, gains, dt, reference, equilibrium)
        local_rows.append({
            "caso": label,
            "kp": gains.kp,
            "ki": gains.ki,
            "kd": gains.kd,
            "referencia_deg": math.degrees(reference),
            "equilibrio_theta_deg": math.degrees(equilibrium.angle),
            "torque_equilibrio_Nm": equilibrium.torque,
            "integral_equilibrio_Nm": equilibrium.integral,
            "integral_activa": gains.ki > 0,
            "dimension_mapa": len(poles),
            "radio_espectral": _spectral_radius(poles),
            "estable_local": _spectral_radius(poles) < 1.0,
            "polos": ";".join(f"{p.real:.10g}{p.imag:+.10g}j" for p in poles),
        })
    _write_csv(output_dir / "polos_locales.csv", local_rows)

    # A P-only sweep spans both the permitted range and analytic Routh limit.
    sweep_rows = []
    for step in range(0, 161):
        kp = step * 0.25
        gains = AnalysisGains(kp)
        eq = equilibria(plant, gains, zero_ref)[0]
        poles = discrete_poles(plant, gains, dt, zero_ref, eq)
        rho = _spectral_radius(poles)
        # La planta no lineal respeta el rango de ganancias del juego; fuera de
        # él se conserva únicamente la exploración del mapa linealizado.
        simulation = simulate(Gains(kp, 0.0, 0.0), dt=dt) if kp <= 10.0 else None
        sweep_rows.append({
            "kp": f"{kp:.2f}",
            "radio_espectral": f"{rho:.12g}",
            "estable_local": int(rho < 1.0),
            "iae_grado_s": f"{simulation.iae:.10g}" if simulation else "",
            "cumple_reto": int(simulation.success) if simulation else "",
            "pico_grados": f"{simulation.peak_degrees:.10g}" if simulation else "",
            "saturacion_pid": f"{simulation.saturation_fraction:.10g}" if simulation else "",
        })
    _write_csv(output_dir / "barrido_kp.csv", sweep_rows)

    # Two-dimensional parameter sweeps around both operating angles. The Kp
    # sweep holds Ki=1; the Ki sweep holds Kp=2. Kd uses three representative
    # values from the game's range. With Ki=0 at 45°, the P-only equilibrium
    # has its calculated static offset rather than being forced to 45°.
    derivative_values = (0.08, 0.5, 3.0)
    controlled_kp_rows = []
    for reference in (zero_ref, step_ref):
        for kd in derivative_values:
            for step in range(0, 41):
                kp = step * 0.25
                gains = AnalysisGains(kp, 1.0, kd)
                equilibrium = equilibria(plant, gains, reference)[0]
                poles = discrete_poles(plant, gains, dt, reference, equilibrium)
                controlled_kp_rows.append({
                    "kp": f"{kp:.2f}", "ki": 1.0, "kd": kd,
                    "referencia_deg": math.degrees(reference),
                    "equilibrio_theta_deg": math.degrees(equilibrium.angle),
                    "integral_equilibrio_Nm": equilibrium.integral,
                    "dimension_mapa": len(poles),
                    "radio_espectral": f"{_spectral_radius(poles):.12g}",
                    "estable_local": int(_spectral_radius(poles) < 1.0),
                })
    _write_csv(output_dir / "barrido_kp_controlado.csv", controlled_kp_rows)

    ki_rows = []
    for reference in (zero_ref, step_ref):
        for kd in derivative_values:
            for step in range(0, 21):
                ki = step * 0.25
                gains = AnalysisGains(2.0, ki, kd)
                equilibrium = equilibria(plant, gains, reference)[0]
                poles = discrete_poles(plant, gains, dt, reference, equilibrium)
                ki_rows.append({
                    "kp": 2.0, "ki": f"{ki:.2f}", "kd": kd,
                    "referencia_deg": math.degrees(reference),
                    "equilibrio_theta_deg": math.degrees(equilibrium.angle),
                    "integral_equilibrio_Nm": equilibrium.integral,
                    "dimension_mapa": len(poles),
                    "radio_espectral": f"{_spectral_radius(poles):.12g}",
                    "estable_local": int(_spectral_radius(poles) < 1.0),
                })
    _write_csv(output_dir / "barrido_ki.csv", ki_rows)

    # Exact digital stability bands in the (Kp, Ki) plane. A 0.5 Kp scan
    # locates every candidate transition in the permitted range; 24 bisection
    # steps refine each observed |z|=1 crossing to better than 3e-8 Kp.
    frontier_ki_values = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
    frontier_rows = []
    for reference in (zero_ref, step_ref):
        for kd in derivative_values:
            for ki in frontier_ki_values:
                if reference == step_ref and ki == 0:
                    # Sin integral, el equilibrio generalmente no coincide con 45°.
                    continue
                intervals, transitions = _stable_intervals_for_slice(
                    plant, dt, 0.0, 10.0, ki, kd, reference,
                    kp_step=0.5, refinements=24)
                if not intervals:
                    frontier_rows.append({
                        "kd": kd, "referencia_deg": math.degrees(reference),
                        "ki": ki, "intervalo_estable": "ninguno",
                        "kp_min_estable": "", "kp_max_estable": "",
                        "limite_inferior_recortado": "", "limite_superior_recortado": "",
                        "transiciones_refinadas": len(transitions),
                    })
                else:
                    for index, (kp_low, kp_high) in enumerate(intervals, 1):
                        frontier_rows.append({
                            "kd": kd, "referencia_deg": math.degrees(reference),
                            "ki": ki, "intervalo_estable": index,
                            "kp_min_estable": f"{kp_low:.9f}",
                            "kp_max_estable": f"{kp_high:.9f}",
                            "limite_inferior_recortado": int(math.isclose(kp_low, 0.0, abs_tol=1e-9)),
                            "limite_superior_recortado": int(math.isclose(kp_high, 10.0, abs_tol=1e-9)),
                            "transiciones_refinadas": len(transitions),
                        })
    _write_csv(output_dir / "fronteras_kp_ki.csv", frontier_rows)

    # Compare selected values with the existing nonlinear, saturated simulator.
    comparison_gains = [
        Gains(0.1, 0.0, 0.0),
        Gains(2.0, 0.0, 0.5),
        Gains(2.0, 1.0, 0.5),
        Gains(10.0, 5.0, 0.5),
        Gains(10.0, 5.0, 3.0),
    ]
    comparison_rows = []
    for gains in comparison_gains:
        equilibrium = equilibria(plant, gains, zero_ref)[0]
        poles = discrete_poles(plant, gains, dt, zero_ref, equilibrium)
        simulation = simulate(gains, dt=dt)
        comparison_rows.append({
            "kp": gains.kp, "ki": gains.ki, "kd": gains.kd,
            "radio_espectral_local_0deg": _spectral_radius(poles),
            "estable_local_0deg": _spectral_radius(poles) < 1.0,
            "iae_grado_s": simulation.iae,
            "cumple_reto": simulation.success,
            "pico_grados": simulation.peak_degrees,
            "fraccion_saturacion_pid": simulation.saturation_fraction,
            "fraccion_saturacion_corriente": simulation.current_saturation_fraction,
            "error_final_deg": math.degrees(simulation.samples[-1].angle
                                             - simulation.samples[-1].reference),
        })
    _write_csv(output_dir / "comparacion_simulacion.csv", comparison_rows)

    sweep_plot = [(float(row["kp"]), float(row["radio_espectral"])) for row in sweep_rows]
    p_only_spectral_bounds = _spectral_bounds([("P-only", sweep_plot, "#1d6da8")])
    _svg_chart(output_dir / "radio_espectral_vs_kp.svg",
               title="Polos del PID digital + planta RK4 (P puro)",
               x_label="Kp (N·m/rad)", y_label="Radio espectral",
               series=[("mapa discreto", sweep_plot, "#1d6da8")],
               x_bounds=(0, 40), y_bounds=p_only_spectral_bounds,
               horizontal=(1.0, "frontera |z| = 1", "#c64747"),
               verticals=[(10.0, "máximo juego 10", "#58a65c"),
                          (kp_analytic["lower_kp"], "P mínimo 0.589", "#db8b27"),
                          (kp_digital_upper, "digital 33.785", "#111111", 0),
                          (kp_analytic["upper_kp"], "Routh 34.529", "#8f5ab5", 18)])

    _svg_chart(output_dir / "iae_vs_kp.svg",
               title="Barrido P-only: polos locales y reto no lineal",
               x_label="Kp (N·m/rad)", y_label="IAE (grados·s, escala logarítmica)",
               series=[("simulación existente", [(float(row["kp"]),
                         max(float(row["iae_grado_s"]), 0.01)) for row in sweep_rows
                        if row["iae_grado_s"]],
                         "#12a18a")],
               x_bounds=(0, 10), y_bounds=(0.1, 10000), log_y=True)

    controlled_kp_series = []
    colors = {0.08: "#1d6da8", 0.5: "#12a18a", 3.0: "#b36038"}
    for kd in derivative_values:
        points = [(float(row["kp"]), float(row["radio_espectral"]))
                  for row in controlled_kp_rows
                  if row["kd"] == kd and row["referencia_deg"] == 0.0]
        controlled_kp_series.append((f"Kd={kd:g}, Ki=1, ref=0°", points, colors[kd]))
    _svg_chart(output_dir / "radio_espectral_kp_kd.svg",
               title="Barrido Kp con acción integral activa",
               x_label="Kp (N·m/rad)", y_label="Radio espectral",
               series=controlled_kp_series,
               x_bounds=(0, 10), y_bounds=_spectral_bounds(controlled_kp_series),
               horizontal=(1.0, "frontera |z| = 1", "#c64747"))

    ki_series = []
    for kd in derivative_values:
        points = [(float(row["ki"]), float(row["radio_espectral"]))
                  for row in ki_rows
                  if row["kd"] == kd and row["referencia_deg"] == 0.0]
        ki_series.append((f"Kd={kd:g}, Kp=2, ref=0°", points, colors[kd]))
    _svg_chart(output_dir / "radio_espectral_ki_kd.svg",
               title="Barrido Ki con Kp=2",
               x_label="Ki (N·m/(rad·s))", y_label="Radio espectral",
               series=ki_series,
               x_bounds=(0, 5), y_bounds=_spectral_bounds(ki_series),
               horizontal=(1.0, "frontera |z| = 1", "#c64747"))

    frontier_colors = {
        0.08: ("#1d6da8", "#79aed6"),
        0.5: ("#11866c", "#75c1ac"),
        3.0: ("#b36038", "#e5a27f"),
    }
    for reference, suffix in ((zero_ref, "0deg"), (step_ref, "45deg")):
        frontier_series = []
        for kd in derivative_values:
            low_color, high_color = frontier_colors[kd]
            entries = [row for row in frontier_rows
                       if row["kd"] == kd
                       and row["referencia_deg"] == math.degrees(reference)
                       and row["intervalo_estable"] == 1]
            lower_points = [(float(row["ki"]), float(row["kp_min_estable"]))
                            for row in entries if row["kp_min_estable"] != ""]
            frontier_series.append((f"Kd={kd:g} · Kp mínimo", lower_points, low_color))
        _svg_chart(output_dir / f"frontera_kp_ki_{suffix}.svg",
                   title=f"Frontera inferior local · referencia {math.degrees(reference):g}°",
                   x_label="Ki (N·m/(rad·s))", y_label="Kp frontera (N·m/rad)",
                   series=frontier_series,
                   x_bounds=(0, 5), y_bounds=(0.35, 1.2))

    summary = {
        "dt_s": dt,
        "duration_s": 15.0,
        "reference_step_s": STEP_TIME,
        "reference_step_degrees": STEP_DEGREES,
        "analytic_p_only_limits": kp_analytic,
        "digital_p_only_upper_boundary": kp_digital_upper,
        "game_kp_max": 10.0,
        "p_critical_upper_outside_game_range": kp_digital_upper > 10.0,
        "local_cases": local_rows,
        "simulation_comparisons": comparison_rows,
        "controlled_kp_sweep_rows": len(controlled_kp_rows),
        "ki_sweep_rows": len(ki_rows),
        "frontier_rows": len(frontier_rows),
        "frontier_ki_values": list(frontier_ki_values),
        "frontier_kp_scan_step": 0.5,
        "frontier_bisection_iterations": 24,
        "eigensolver": "numpy.linalg.eigvals" if _numpy is not None else "stdlib Durand-Kerner",
    }
    (output_dir / "resumen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_report(output_dir / "informe_estabilidad.md", summary)
    return summary


def _write_report(path: Path, summary: dict) -> None:
    limits = summary["analytic_p_only_limits"]
    cases = summary["local_cases"]
    comparisons = summary["simulation_comparisons"]
    lines = [
        "# Análisis local de estabilidad del PID digital",
        "",
        "## Alcance y método",
        "",
        "Se linealizó el mapa de una muestra del juego alrededor de equilibrios de referencia fija. "
        "La matriz incluye el filtro de velocidad con actualización exponencial, la integral Euler "
        "explícita solo cuando Ki>0 y el RK4 de ángulo, velocidad y corriente con tensión retenida. "
        "Los polos se obtienen de esa matriz discreta; estabilidad local significa radio espectral menor que 1.",
        "",
        f"Se usó dt={summary['dt_s']:g} s. El análisis supone que la petición PID, el voltaje y la corriente "
        f"están lejos de sus límites; no incluye el cambio de modo del anti-windup en la frontera. "
        f"Solver de polos: {summary['eigensolver']}.",
        "",
        "## Equilibrios y estado integral",
        "",
        "Con Ki=0, la contribución integral queda exactamente en cero desde la inicialización del juego y "
        "se elimina de la matriz; el mapa tiene cuatro estados. Con Ki>0 se conserva la contribución integral "
        "como quinto estado. En seguimiento exacto, el equilibrio a 0° requiere I=0 y el de 45° requiere "
        "el torque integral que compensa la gravedad.",
        "",
        "| Caso | Ki | Ref. | θ equilibrio | I equilibrio | ρ(A) | Estabilidad local |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in cases:
        integral_value = row["integral_equilibrio_Nm"]
        integral_label = "inactiva" if integral_value is None else f"{integral_value:.6f} N·m"
        lines.append(f"| {row['caso']} | {row['ki']:g} | {row['referencia_deg']:g}° | "
                     f"{row['equilibrio_theta_deg']:.5f}° | {integral_label} | "
                     f"{row['radio_espectral']:.8f} | {'sí' if row['estable_local'] else 'no'} |")
    lines.extend([
        "",
        "Para Ki=0 con referencia distinta de cero, el equilibrio P-only generalmente tiene error estático; "
        "el script lo calcula resolviendo Kp(r−θ)+mgl·sin(θ)=0. No se fuerza θ=r cuando el integrador está apagado.",
        "",
        "## Frontera digital Kp–Ki",
        "",
        "Para Kd=0,08 / 0,5 / 3 y referencias de 0° y 45°, se recorrió Ki=0, 1, 2, 3, 4 y 5. "
        "En cada corte se evaluó el radio espectral cada 0,5 de Kp entre 0 y 10; todo cambio detectado "
        "entre estable e inestable se refinó con 24 bisecciones sobre los polos del mapa discreto. "
        "Las bandas reportadas son locales, suponen que el equilibrio no satura y están recortadas al rango Kp del juego. "
        "La malla puede omitir una banda más estrecha que 0,5 de Kp si no contiene un punto de prueba estable.",
        "",
        "",
        "## Límite analítico de P",
        "",
        "Como comparación de pizarra se eliminan Ki, Kd, filtro, muestreo, saturaciones y no linealidades, "
        "pero se conserva el motor DC linealizado y la amortiguación efectiva b_eff=b+Fc/vs. El polinomio P-only es",
        "",
        "```text",
        "J L s³ + (J R + b_eff L)s² + (b_eff R − mgl L + Kt Ke)s + R(Kp − mgl) = 0",
        "```",
        "",
        f"Routh–Hurwitz da {limits['lower_kp']:.6f} < Kp < {limits['upper_kp']:.6f} N·m/rad "
        f"para estabilidad continua local P-only. La cota superior queda por encima del máximo actual "
        f"del control deslizante (10), por un factor {limits['upper_kp']/10:.2f}. Este resultado no cambia "
        "la validación ni el rango permitido por el juego. Para el mapa digital exacto (filtro + RK4), "
        f"la bisección de polos da una frontera superior Kp≈{summary['digital_p_only_upper_boundary']:.8f}; "
        "también queda fuera de la interfaz. Esta frontera discreta se calcula sobre un P-only sin saturación, "
        "por lo que no sustituye la evaluación no lineal del reto.",
        "",
        "## Comparación con el simulador existente",
        "",
        "El radio espectral solo describe perturbaciones pequeñas alrededor de un equilibrio. El reto completo "
        "parte de ω(0)=2 rad/s, aplica límites del actuador y cambia la referencia a 45° en t=5 s. Por eso "
        "la clasificación local puede diferir del resultado del intento.",
        "",
        "| Kp / Ki / Kd | ρ local en 0° | IAE (°·s) | Cumple reto | Pico (°) | Saturación PID |",
        "|---|---:|---:|---|---:|---:|",
    ])
    for row in comparisons:
        lines.append(f"| {row['kp']:g} / {row['ki']:g} / {row['kd']:g} | "
                     f"{row['radio_espectral_local_0deg']:.8f} | {row['iae_grado_s']:.6f} | "
                     f"{'sí' if row['cumple_reto'] else 'no'} | {row['pico_grados']:.3f} | "
                     f"{100*row['fraccion_saturacion_pid']:.2f}% |")
    lines.extend([
        "",
        "## Archivos",
        "",
        "- `polos_locales.csv`: polos complejos, equilibria, radio espectral y dimensión del mapa.",
        "- `barrido_kp.csv`: polos P-only cada 0,25 hasta Kp=40, con simulaciones existentes solo para el rango permitido 0–10.",
        "- `barrido_kp_controlado.csv` y `barrido_ki.csv`: barridos de Kp y Ki con Kd=0,08 / 0,5 / 3, en equilibrios de referencia 0° y 45°.",
        "- `fronteras_kp_ki.csv`: intervalos estables en Kp para cada punto Ki, Kd y referencia; cruces de |z|=1 refinados por bisección.",
        "- `comparacion_simulacion.csv`: candidatos comparados con `pid_game.simulation.simulate` sin modificarlo.",
        "- `frontera_kp_ki_0deg.svg` y `frontera_kp_ki_45deg.svg`: frontera inferior de Kp frente a Ki; no se detectó frontera superior en el intervalo Kp ≤ 10. El gráfico de 45° excluye Ki=0, que no sigue exactamente esa referencia.",
        "- `radio_espectral_vs_kp.svg`, `radio_espectral_kp_kd.svg`, `radio_espectral_ki_kd.svg` e `iae_vs_kp.svg`: gráficas SVG generadas con SVG/stdlib.",
        "- `resumen.json`: parámetros y resultados completos en formato legible por máquina.",
        "",
        "Reproducir desde la raíz del proyecto con `python -m tools.analisis_estabilidad`. El script solo escribe en `artifacts/analisis_estabilidad/`.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "artifacts" / "analisis_estabilidad")
    parser.add_argument("--dt", type=float, default=DT)
    args = parser.parse_args(argv)
    summary = run_analysis(args.output_dir, args.dt)
    limits = summary["analytic_p_only_limits"]
    print(f"Informe: {args.output_dir / 'informe_estabilidad.md'}")
    print(f"Cota analítica P-only: {limits['lower_kp']:.6f} < Kp < {limits['upper_kp']:.6f}; "
          f"máximo actual del juego=10")
    print(f"Barrido y comparación guardados en {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
