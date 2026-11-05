import math

import pytest

from pid_game.actuator import DCMotor
from pid_game.controller import Gains
from pid_game.simulation import (
    BAND,
    DURATION,
    STEP_DEGREES,
    STEP_TIME,
    Sample,
    evaluate,
    iae_segment,
    response_metrics,
    simulate,
)


def sample_with_error(time: float, error_degrees: float) -> Sample:
    """Crea una muestra con error conocido respecto de la referencia vigente."""
    reference = math.radians(STEP_DEGREES if time >= STEP_TIME else 0.0)
    angle = reference + math.radians(error_degrees)
    return Sample(time, angle, 0.0, 0.0, reference)


def test_response_metrics_report_post_step_overshoot_and_last_settling_entry():
    samples = tuple(
        sample_with_error(time, error)
        for time, error in (
            (0.0, 0.0),
            (4.9, 0.0),
            (5.0, -15.0),  # La referencia cambia aquí; no es sobreimpulso positivo.
            (5.1, 12.0),
            (5.2, -6.0),
            (5.3, 5.0),
            (5.4, -4.9),
            (5.5, 5.01),  # Una nueva salida de banda retrasa el asentamiento.
            (5.6, -5.0),
            (5.7, 4.8),
        )
    )

    metrics = response_metrics(samples)

    assert metrics.overshoot_degrees == pytest.approx(12.0)
    assert metrics.settling_time == pytest.approx(0.6)
    assert abs(math.degrees(samples[-2].angle - samples[-2].reference)) == pytest.approx(BAND)


def test_post_step_crossings_use_hysteresis_and_ignore_reference_jump_and_chatter():
    samples = tuple(
        sample_with_error(time, error)
        for time, error in (
            (4.9, 4.0),  # El lado anterior al escalón no inicializa el contador.
            (5.0, -8.0),  # Inicializa el lado; el salto de referencia no cuenta.
            (5.1, -0.4),
            (5.2, 0.8),
            (5.3, 1.1),  # Cruce 1: salió de la histéresis por el lado positivo.
            (5.4, 0.2),
            (5.5, -0.9),  # Ruido dentro de ±1° no cambia el lado ni rearma.
            (5.6, -1.2),  # Cruce 2.
            (5.7, -0.1),
            (5.8, 0.7),
            (5.9, -0.8),  # Sigue dentro de la zona muerta.
            (6.0, 1.1),  # Cruce 3.
        )
    )

    metrics = response_metrics(samples)

    assert metrics.post_step_crossings == 3
    assert metrics.overshoot_degrees == pytest.approx(1.1)


def test_response_metrics_handle_missing_or_single_post_step_sample():
    before_step = response_metrics((sample_with_error(4.9, 3.0),))
    inside_band = response_metrics((sample_with_error(STEP_TIME, BAND),))
    outside_band = response_metrics((sample_with_error(STEP_TIME, BAND + 0.01),))

    assert before_step.post_step_crossings == 0
    assert before_step.overshoot_degrees == 0
    assert before_step.settling_time is None
    assert inside_band.settling_time == 0
    assert outside_band.settling_time is None


def test_simulation_exposes_diagnostics_without_changing_existing_score_or_torque():
    result = simulate(Gains(2, 1, 0.5))
    metrics = response_metrics(result.samples)
    step_samples = result.samples[1:]
    iae, success = evaluate(result.samples)

    assert result.samples[0].time == 0.0
    assert result.samples[-1].time == DURATION
    assert result.iae == pytest.approx(iae)
    assert result.iae == pytest.approx(
        sum(iae_segment(a, b) for a, b in zip(result.samples, result.samples[1:]))
    )
    assert result.success is success
    assert result.success and result.iae < 50

    assert result.post_step_crossings == metrics.post_step_crossings
    assert result.overshoot_degrees == pytest.approx(metrics.overshoot_degrees)
    assert result.settling_time == metrics.settling_time
    assert result.saturation_fraction == pytest.approx(result.pid_saturation_fraction)
    assert result.pid_saturation_fraction == pytest.approx(
        sum(sample.pid_saturated for sample in step_samples) / len(step_samples)
    )
    assert result.current_saturation_fraction == pytest.approx(
        sum(sample.current_saturated for sample in step_samples) / len(step_samples)
    )
    assert result.max_current == pytest.approx(
        max(abs(sample.current) for sample in result.samples)
    )
    assert result.min_integral == pytest.approx(
        min(sample.integral for sample in result.samples)
    )
    assert result.max_integral == pytest.approx(
        max(sample.integral for sample in result.samples)
    )

    # `torque` conserva su significado histórico: torque real del motor, no
    # el torque PID solicitado antes de los límites eléctricos.
    motor = DCMotor()
    assert all(
        sample.torque == pytest.approx(motor.torque_constant * sample.current)
        for sample in result.samples
    )
    assert all(abs(sample.pid_torque) <= 2.0 + 1e-12 for sample in result.samples)
