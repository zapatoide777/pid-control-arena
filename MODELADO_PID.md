# Modelo del péndulo y motor DC

El juego representa un motor DC idealizado acoplado directamente al pivote de un péndulo rígido. Sus parámetros son supuestos didácticos, no valores identificados de un motor real. La medición de ángulo y velocidad es perfecta y no hay ruido, holgura, PWM ni flexibilidad. No se trata de un carro-péndulo.

## Mecánica y signos

Con θ medida desde la vertical superior, positiva hacia la derecha, y torque positivo en el mismo sentido:

```text
J θ̈ = m g l sin(θ) − b θ̇ − Fc tanh(θ̇/vs) + Kt i
```

`m=0,2 kg`, `l=0,3 m`, `J=0,024 kg·m²` (inercia total en el pivote), `b=0,01 N·m·s/rad`, `g=9,81 m/s²`, `Fc=0,015 N·m` y `vs=0,02 rad/s`. La gravedad amplifica una desviación positiva cerca de la vertical. La fricción seca suavizada aproxima Coulomb en movimiento, pero no representa adherencia estática. La energía mecánica `E=Jω²/2 + mgl cos θ` satisface `Ė=Kt i ω−bω²−Fc tanh(ω/vs)ω`.

## Actuador

```text
L di/dt = V − R i − Ke ω
τmotor = Kt i
```

`R=2 Ω`, `L=0,16 H`, `Kt=1/3 N·m/A`, `Ke=1/3 V·s/rad`, tensión solicitada limitada a ±12 V y corriente limitada a ±6 A; por tanto, el torque está limitado a ±2 N·m. La petición PID de torque `q` se convierte en tensión mediante `V=clip(R q/Kt, −12, 12)`. Esta conversión es una calibración a velocidad cero, sin compensación de fuerza contraelectromotriz ni lazo de corriente.

El límite de corriente es ideal: al alcanzar ±6 A se proyecta la corriente y se impide que siga creciendo hacia afuera; se permite descargarla. Durante esa limitación la ecuación eléctrica no describe por sí sola la tensión física efectiva del controlador. El voltaje almacenado en las muestras es el solicitado, después de limitar la alimentación; no es una medición de la tensión efectiva del circuito de protección.

## Control digital y referencia

El PID paralelo usa `e=r−θ` y derivada sobre medición para evitar la patada derivativa:

```text
ωf[k] = ωf[k−1] + (1 − exp(−dt/0,02)) (ω[k]−ωf[k−1])
q = clip(Kp e + I − Kd ωf, −2, 2)
ΔI = Ki e dt
```

La integral se congela cuando el incremento aumentaría la saturación de la **petición PID** y se permite descargarla. No es anti-windup de seguimiento de la corriente real ni del voltaje efectivo. Kp, Ki y Kd se expresan respectivamente en N·m/rad, N·m/(rad·s) y N·m·s/rad.

La referencia es 0° hasta t=4 s, cuando salta a 8°. La perturbación inicial común es `θ(0)=0`, `ω(0)=2 rad/s` e `i(0)=0`. Es una condición inicial equivalente a un impulso angular `JΔω=0,048 N·m·s`, no una fuerza finita simulada.

El controlador se actualiza cada 1 ms; la tensión se retiene durante la muestra. RK4 integra conjuntamente ángulo, velocidad y corriente, con proyección de corriente en las etapas. El integrador del PID usa Euler y el filtro derivativo usa una actualización exponencial. Reducir el paso cambia también el periodo del controlador.

## Evaluación y límite de validez

La prueba dura 10 s; el IAE integra `|θ−r|` mediante trapecios en grados·segundo. El salto ocurre exactamente en una frontera de muestra; el intervalo anterior usa la referencia antigua. Se marca una caída al alcanzar ±90°, sin detener la integración. Se exige ausencia de caída y error dentro de ±5° durante todo el último segundo. El ranking usa únicamente el tercer intento y ordena por IAE.

Para pequeños ángulos y velocidades, `b_eff=b+Fc/vs=0,76 N·m·s/rad`. Si se eliminan saturaciones y se toma la linealización local:

```text
(Js² + b_eff s − mgl) Θ = Kt I
(Ls + R) I = V − Ke s Θ
Θ/Q = R / [(Js² + b_eff s − mgl)(Ls+R) + Kt Ke s]
```

La última expresión usa la conversión `V=R Q/Kt` y no incluye el PID. Sirve solo cerca del equilibrio y fuera de los límites; la simulación usa el seno no lineal y la fricción suavizada.

Referencias: [modelo de motor DC de MathWorks](https://www.mathworks.com/help/simscape-electrical/ref/dcmotor.html) y [péndulo invertido de CTMS](https://ctms.engin.umich.edu/CTMS/index.php?example=InvertedPendulum&section=ControlPID), este último sobre un carro y no sobre el actuador directo usado aquí.
