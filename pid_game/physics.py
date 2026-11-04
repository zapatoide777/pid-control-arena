"""Péndulo invertido no lineal con fricción en el pivote (SI)."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Plant:
    mass: float = .2
    length: float = .3
    inertia: float = .024
    damping: float = .01
    gravity: float = 9.81
    coulomb_friction: float = .015
    friction_speed: float = .02

    def acceleration(self, angle, velocity, torque):
        return (self.mass*self.gravity*self.length*math.sin(angle)
                - self.damping*velocity
                - self.coulomb_friction*math.tanh(velocity/self.friction_speed)
                + torque) / self.inertia

    def step(self, angle, velocity, torque, dt):
        def f(a, w):
            return w, self.acceleration(a, w, torque)
        a1, w1 = f(angle, velocity)
        a2, w2 = f(angle+dt*a1/2, velocity+dt*w1/2)
        a3, w3 = f(angle+dt*a2/2, velocity+dt*w2/2)
        a4, w4 = f(angle+dt*a3, velocity+dt*w3)
        return (angle+dt*(a1+2*a2+2*a3+a4)/6,
                velocity+dt*(w1+2*w2+2*w3+w4)/6)
