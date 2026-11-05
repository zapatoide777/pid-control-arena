"""Pruebas locales del análisis lineal del péndulo y el motor DC."""
import math

import pytest

from pid_game.actuator import DCMotor
from pid_game.controller import Gains, PID
from pid_game.physics import Plant
from tools.analisis_estabilidad import discrete_poles, equilibria, linearized_map


def _closed_loop_step(state, plant, gains, dt, reference):
    """Avanza una muestra usando los componentes reales, sin envoltura angular."""
    angle, velocity, current, filtered_velocity, *integral_state = state
    controller = PID(gains)
    controller.filtered_velocity = filtered_velocity
    if gains.ki > 0:
        controller.integral = integral_state[0]

    motor = DCMotor()
    requested_torque = controller.command(angle, velocity, dt, reference)
    voltage = motor.voltage(requested_torque)
    next_angle, next_velocity, next_current = motor.step(
        plant, angle, velocity, current, voltage, dt
    )
    next_state = [
        next_angle,
        next_velocity,
        next_current,
        controller.filtered_velocity,
    ]
    if gains.ki > 0:
        next_state.append(controller.integral)
    return next_state


def test_discrete_jacobian_matches_centered_finite_differences():
    plant = Plant()
    gains = Gains(2, 0.2, 0.4)
    dt = 0.001
    equilibrium = equilibria(plant, gains, 0.0)[0]
    state = [equilibrium.angle, equilibrium.velocity, equilibrium.current, 0.0,
             equilibrium.integral]

    jacobian = linearized_map(plant, gains, dt, 0.0, equilibrium)
    finite_difference = [[0.0 for _ in state] for _ in state]
    epsilon = 1e-6
    for column in range(len(state)):
        plus, minus = state.copy(), state.copy()
        plus[column] += epsilon
        minus[column] -= epsilon
        output_plus = _closed_loop_step(plus, plant, gains, dt, 0.0)
        output_minus = _closed_loop_step(minus, plant, gains, dt, 0.0)
        for row in range(len(state)):
            finite_difference[row][column] = (
                output_plus[row] - output_minus[row]
            ) / (2 * epsilon)

    assert len(jacobian) == len(state)
    assert all(len(row) == len(state) for row in jacobian)
    for analytic_row, numeric_row in zip(jacobian, finite_difference):
        assert analytic_row == pytest.approx(numeric_row, rel=2e-6, abs=2e-8)


def test_zero_integral_gain_omits_integrator_state_and_uses_p_only_equilibrium():
    plant = Plant()
    gains = Gains(2, 0, 0.4)
    reference = math.radians(8)
    equilibrium, = equilibria(plant, gains, reference)

    # With Ki=0, the static P-only balance need not track a nonzero reference.
    assert equilibrium.angle != pytest.approx(reference, abs=1e-4)
    assert equilibrium.velocity == pytest.approx(0.0, abs=1e-12)
    assert equilibrium.torque == pytest.approx(
        gains.kp * (reference - equilibrium.angle), abs=1e-10
    )
    assert plant.acceleration(
        equilibrium.angle, equilibrium.velocity, equilibrium.torque
    ) == pytest.approx(0.0, abs=1e-10)
    assert equilibrium.integral is None

    matrix = linearized_map(plant, gains, 0.001, reference, equilibrium)
    poles = discrete_poles(plant, gains, 0.001, reference, equilibrium)
    assert len(matrix) == 4
    assert all(len(row) == 4 for row in matrix)
    assert len(poles) == 4


def test_equilibrium_reports_following_torque_and_motor_operating_point():
    plant = Plant()
    motor = DCMotor()
    gains = Gains(2, 0.2, 0.4)
    reference = math.radians(8)
    equilibrium, = equilibria(plant, gains, reference)
    gravity_torque = -plant.mass * plant.gravity * plant.length * math.sin(reference)

    assert equilibrium.angle == pytest.approx(reference, abs=1e-12)
    assert equilibrium.velocity == pytest.approx(0.0, abs=1e-12)
    assert equilibrium.torque == pytest.approx(gravity_torque, abs=1e-12)
    assert equilibrium.current == pytest.approx(
        gravity_torque / motor.torque_constant, abs=1e-12
    )
    assert equilibrium.voltage == pytest.approx(
        motor.resistance * equilibrium.current, abs=1e-12
    )
    assert equilibrium.integral == pytest.approx(gravity_torque, abs=1e-12)
    assert plant.acceleration(
        equilibrium.angle, equilibrium.velocity, equilibrium.torque
    ) == pytest.approx(0.0, abs=1e-12)


def test_known_local_stability_and_open_loop_instability():
    plant = Plant()
    dt = 0.001
    zero_reference = 0.0
    stable_gains = Gains(2, 0.2, 0.4)
    stable_poles = discrete_poles(plant, stable_gains, dt, zero_reference)
    assert len(stable_poles) == 5
    assert max(abs(pole) for pole in stable_poles) < 1.0

    open_loop_poles = discrete_poles(plant, Gains(0, 0, 0), dt, zero_reference)
    assert len(open_loop_poles) == 4
    assert max(abs(pole) for pole in open_loop_poles) > 1.0
