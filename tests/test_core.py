import math
from dataclasses import replace

import pytest

from pid_game.controller import Gains, PID
from pid_game.physics import Plant
from pid_game.actuator import DCMotor
from pid_game.simulation import Sample, evaluate, hint, simulate, DURATION, DT, STABLE_FROM, INITIAL_VELOCITY, STEP_TIME, STEP_DEGREES, iae_segment
from pid_game.game import Game, State, Phase


def test_equilibrium_unstable_gravity_and_corrective_torque():
    plant = Plant()
    assert plant.step(0, 0, 0, .001) == (0, 0)
    assert plant.acceleration(.1, 0, 0) > 0
    command = PID(Gains(2, 0, 0)).command(.1, 0, .001)
    assert command < 0
    assert plant.acceleration(.1, 0, command) < 0
    assert plant.acceleration(-.1, 0, 0) < 0


def test_rk4_against_constant_acceleration_solution():
    plant = Plant(gravity=0, damping=0, coulomb_friction=0)
    angle, velocity = plant.step(.3, .4, .24, .01)
    assert angle == pytest.approx(.3 + .4*.01 + 10*.01**2/2)
    assert velocity == pytest.approx(.4 + 10*.01)


def test_demo_fails_but_known_controller_recovers():
    demo, good = simulate(Gains()), simulate(Gains(2, .2, .4))
    assert demo.fallen and not demo.success and demo.iae > 300
    assert good.success and not good.fallen and good.iae < 25
    assert hint(good) == ""
    assert "cayó" in hint(demo)
    assert len(demo.samples) == len(good.samples) == round(DURATION/DT)+1
    assert demo.samples[-1].time == DURATION
    assert demo.peak_degrees > 180  # nunca envuelve el ángulo al caer


@pytest.mark.parametrize("gains", [Gains(), Gains(2, .2, .4), Gains(10, 5, 3)])
def test_timestep_convergence(gains):
    coarse, fine = simulate(gains), simulate(gains, dt=.0005)
    assert coarse.success == fine.success
    assert coarse.fallen == fine.fallen
    assert coarse.iae == pytest.approx(fine.iae, rel=.03, abs=.015)
    finer = simulate(gains, dt=.00025)
    # La demo caída es sensible al periodo digital; verificar tendencia, no
    # exigir el mismo error absoluto que en una trayectoria estable.
    error_coarse = abs(coarse.samples[-1].angle - fine.samples[-1].angle)
    error_fine = abs(fine.samples[-1].angle - finer.samples[-1].angle)
    assert error_coarse < .35
    assert error_fine < error_coarse + 1e-9


def test_iae_absolute_and_full_window_stability():
    # |+1| y |-1| se suman (trapezoides), nunca se cancelan.
    samples = tuple(Sample(t, math.radians(a), 0, 0)
                    for t, a in [(0, 1), (STABLE_FROM, -1),
                                 (STABLE_FROM+.5, 1), (DURATION, -1)])
    iae, success, fallen = evaluate(samples)
    assert iae == pytest.approx(DURATION)
    assert success and not fallen
    boundary = (Sample(0, 0, 1, 0), Sample(STABLE_FROM, math.radians(5), 0, 0),
                Sample(DURATION, 0, 0, 0))
    assert evaluate(boundary)[1]
    spike = boundary[:2] + (Sample(STABLE_FROM+.5, math.radians(5.01), 0, 0),) + boundary[2:]
    assert not evaluate(spike)[1]
    early_fall = (Sample(0, 0, 0, 0), Sample(1, math.pi/2, 0, 0)) + boundary[1:]
    assert evaluate(early_fall)[2]
    assert not evaluate(early_fall)[1]


def test_controller_limits_filter_and_antiwindup_recovery():
    pid = PID(Gains(10, 5, 3))
    for _ in range(1000):
        assert pid.command(10, 0, .001) == -2
    assert pid.integral == 0
    assert pid.saturated
    # Invertir el error no deja acumulación oculta que mantenga el torque incorrecto.
    assert pid.command(-10, 0, .001) == 2
    derivative = PID(Gains(0, 0, 1))
    first = derivative.command(0, 1, .001)
    assert -1 < first < 0
    for _ in range(1000):
        derivative.command(0, 1, .001)
    assert derivative.filtered_velocity == pytest.approx(1)
    assert not derivative.saturated


@pytest.mark.parametrize("values", [(-1, 0, 0), (11, 0, 0), (0, 6, 0), (0, 0, 4), (float('nan'), 0, 0)])
def test_gain_validation(values):
    with pytest.raises(ValueError):
        Gains(*values)


def test_contextual_hint_for_oscillation_and_saturation():
    result = simulate(Gains())
    samples = tuple(Sample(i*DT, math.radians(8)*math.sin(i*.02), 0, 2)
                    for i in range(round(DURATION/DT)+1))
    response = replace(result, samples=samples, fallen=False, saturation_fraction=.3)
    message = hint(response)
    assert "Oscila" in message and "Kd" in message
    assert len(message) < 100


def test_exactly_three_attempts_demo_free_cooldown_and_final_only():
    game = Game()
    assert game.state is State.WAITING
    game.begin("  Martín  ")
    with pytest.raises(RuntimeError):
        game.complete_demo(skipped=True)
    assert game.attempts == []
    game.complete_demo()
    assert game.demo_seen and len(game.attempts) == 0
    first = game.launch(Gains(2, .2, .4))
    with pytest.raises(RuntimeError):
        game.launch(Gains())
    game.finish_playback(10)
    assert game.ready_at == 10  # éxito: sin espera ni pistas
    game.continue_editing(10)
    second = game.launch(Gains())
    game.finish_playback(20)
    assert game.ready_at == 23
    with pytest.raises(RuntimeError):
        game.continue_editing(22.999)
    game.continue_editing(23)
    assert game.gains == second.gains
    third = game.launch(Gains(1, 0, .2))
    game.finish_playback(30)
    assert len(game.attempts) == 3
    assert game.state is State.FINISHED
    assert game.final is third and game.final is not first
    with pytest.raises(RuntimeError):
        game.launch(Gains())
    game.reset()
    game.begin("")
    game.complete_demo(skipped=True)
    assert game.alias == "Jugador" and game.phase is Phase.EDITING
    assert game.attempts == []


def test_every_trial_resets_physics_and_integral():
    first, second = simulate(Gains(1, .5, .3)), simulate(Gains(1, .5, .3))
    assert first == second
    assert first.samples[0] == Sample(0, 0, INITIAL_VELOCITY, 0)


def test_nonlinear_balance_energy_and_linearized_routh_condition():
    plant = Plant()
    theta, omega, torque = .03, .7, -.4
    # El residual de balance es cero, incluyendo peso y amortiguamiento.
    acceleration = plant.acceleration(theta, omega, torque)
    residual = (plant.inertia*acceleration - plant.mass*plant.gravity*plant.length*math.sin(theta)
                + plant.damping*omega + plant.coulomb_friction*math.tanh(omega/plant.friction_speed) - torque)
    assert residual == pytest.approx(0, abs=1e-14)
    # Potencia: E_dot = u*omega - b*omega² para E=Jω²/2+mgl cosθ.
    energy_rate = (plant.inertia*acceleration - plant.mass*plant.gravity*plant.length*math.sin(theta))*omega
    assert energy_rate == pytest.approx(torque*omega - plant.damping*omega**2 - plant.coulomb_friction*math.tanh(omega/plant.friction_speed)*omega)
    # Jacobiano de la gravedad en θ=0 da el polo de lazo abierto positivo.
    gain_gravity = (plant.acceleration(1e-5, 0, 0)-plant.acceleration(-1e-5, 0, 0))/(2e-5)
    assert gain_gravity == pytest.approx(plant.mass*plant.gravity*plant.length/plant.inertia, rel=1e-9)
    assert gain_gravity > 0
    # C(s)=Kp+Ki/s+Kd*s: para el cúbico ideal, Routh exige
    # (b+Kd)(Kp-mgl)>J*Ki, además de términos positivos.
    gains = Gains(2, .2, .4)
    a2, a1, a0 = plant.damping+gains.kd, gains.kp-plant.mass*plant.gravity*plant.length, gains.ki
    assert a2 > 0 and a1 > 0 and a0 > 0 and a2*a1 > plant.inertia*a0
    assert a2*a1 == pytest.approx(.578674)
    failing_ki = (a2*a1/plant.inertia)+1e-3
    assert a2*a1 < plant.inertia*failing_ki


def test_dc_motor_electrical_response_back_emf_and_limits():
    motor = DCMotor()
    assert motor.voltage(100) == 12 and motor.voltage(-100) == -12
    assert motor.current_derivative(0, 3, 0) < 0  # fuerza contraelectromotriz
    assert motor.current_derivative(6, 0, 12) == 0
    assert motor.current_derivative(6, 0, -12) < 0  # permite descargar
    plant = Plant(gravity=0, damping=0, inertia=1e12, coulomb_friction=0)
    angle, velocity, current = motor.step(plant, 0, 0, 0, 12, .001)
    exact = 6 * (1-math.exp(-.001*2/.16))
    assert current == pytest.approx(exact, abs=1e-8)
    _, _, limited = motor.step(plant, 0, -100, 6, 12, .001)
    assert limited <= motor.current_limit


def test_reference_step_error_integral_and_derivative_no_kick():
    assert STEP_TIME == 4 and STEP_DEGREES == 8
    old = Sample(3.999, 0, 0, 0, 0)
    changed = Sample(4.0, 0, 0, 0, math.radians(8))
    after = Sample(4.001, 0, 0, 0, math.radians(8))
    assert iae_segment(old, changed) == 0
    assert iae_segment(changed, after) == pytest.approx(.008)
    pid = PID(Gains(0, 0, 1))
    assert pid.command(0, 0, .001, math.radians(8)) == 0
    result = simulate(Gains(2, .2, .4))
    assert result.samples[3999].reference == 0
    assert result.samples[4000].reference == pytest.approx(math.radians(8))
    assert result.iae == pytest.approx(sum(iae_segment(a,b) for a,b in zip(result.samples,result.samples[1:])))


def test_actuator_delay_makes_high_gains_distinct_from_good_tuning():
    good = simulate(Gains(2, .2, .4))
    aggressive = simulate(Gains(10, 5, 3))
    assert good.success and not good.fallen
    assert not aggressive.success and aggressive.iae > 2*good.iae
    assert all(abs(s.torque) <= 2 + 1e-12 for s in aggressive.samples)
    assert all(abs(s.current) <= 6 + 1e-12 and abs(s.voltage) <= 12 + 1e-12
               for s in aggressive.samples)


def test_success_uses_error_relative_to_step_reference():
    samples = (Sample(0, 0, 0, 0),
               Sample(STABLE_FROM, 0, 0, 0, math.radians(8)),
               Sample(DURATION, 0, 0, 0, math.radians(8)))
    assert not evaluate(samples)[1]
