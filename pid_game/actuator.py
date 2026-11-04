"""Motor DC directo al pivote; limitador de corriente ideal."""
from dataclasses import dataclass

@dataclass(frozen=True)
class DCMotor:
    resistance: float = 2.0
    inductance: float = .16
    torque_constant: float = 1/3
    back_emf_constant: float = 1/3
    voltage_limit: float = 12.0
    current_limit: float = 6.0

    def clamp_current(self, current):
        return max(-self.current_limit, min(self.current_limit, current))

    def voltage(self, torque):
        return max(-self.voltage_limit, min(self.voltage_limit,
                   torque*self.resistance/self.torque_constant))

    def current_derivative(self, current, velocity, voltage):
        derivative = (voltage-self.resistance*current-self.back_emf_constant*velocity)/self.inductance
        if (current >= self.current_limit and derivative > 0) or (current <= -self.current_limit and derivative < 0):
            return 0.0
        return derivative

    def step(self, plant, angle, velocity, current, voltage, dt):
        def f(a, w, i):
            i = self.clamp_current(i)
            return (w, plant.acceleration(a, w, self.torque_constant*i),
                    self.current_derivative(i, w, voltage))
        state = (angle, velocity, current)
        def advance(s, k, h):
            return tuple(a+h*b for a,b in zip(s,k))
        k1 = f(*state)
        k2 = f(*advance(state, k1, dt/2))
        k3 = f(*advance(state, k2, dt/2))
        k4 = f(*advance(state, k3, dt))
        result = tuple(a+dt*(b+2*c+2*d+e)/6 for a,b,c,d,e in zip(state,k1,k2,k3,k4))
        return result[0], result[1], self.clamp_current(result[2])
