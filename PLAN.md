# Juego educativo de sintonización PID — plan aprobado

## Objetivo y reglas
Aplicación de escritorio Python en español para principiantes. Péndulo con torque ideal en pivote, referencia 0°, mismo empujón en todas las pruebas. Demostración inicial con PID malo sin consumir intentos, omisible después de verla una vez. Tres intentos con ganancias fijas durante la ejecución; solo el tercero produce el resultado del ranking.

Éxito: permanecer en ±5° durante todo [5, 6] s sin haber caído. Pistas únicamente tras fallos. En intentos 1 y 2, espera mínima de 3 segundos antes de permitir continuar; pista visible hasta pulsar. Tras el tercero, resultado final con pista si falló.

## Planta y controlador
J θ'' = m g l sin(θ) − b θ' + u; e = −θ.
m=0.2 kg; l=0.3 m al centro de masa; J=0.024 kg m²; b=0.01 N m s/rad; g=9.81 m/s².
θ(0)=0; θ'(0)=2 rad/s; horizonte 6 s; RK4 de paso fijo 1 ms.
PID paralelo, derivada sobre medición con filtro 20 ms, torque limitado ±2 N m y anti-windup por integración condicional.
Ganancias no negativas: Kp 0–10, Ki 0–5, Kd 0–3; resolución 0.01, unidades visibles. Demostración Kp=0.1, Ki=0, Kd=0.
Caída al alcanzar ±90°: marcar y continuar los 6 s completos. Ángulo sin envolver.
IAE = integral de |θ−r| en [0,6], expresado en grados·segundo. Menor es mejor. Ranking exclusivamente por IAE, sin penalización extra por caída.

## Interfaz
PySide6, animación QPainter y gráfica temporal Qt Charts. Simulación, controlador, reglas e interfaz separados; sin API pública ni conexión de red durante el juego.
Tres estados principales: en espera (alias/instrucciones/inicio), jugando (demostración/edición/ejecución/devolución), juego terminado (resultado/ranking).
Mostrar péndulo, gráfica con referencia y banda ±5°, tiempo e intento. Reproducción real independiente del paso físico. Conservar ganancias anteriores entre intentos.
Pistas basadas en oscilación, error creciente y saturación, como sugerencias sin atribuciones causales absolutas.
Tabla y gráfico top 10 histórico; resultado actual visible y resaltado aunque esté fuera. Guardar alias, fecha, ganancias, IAE, éxito/caída; empates por orden de registro. Nueva partida y salir.

## Entrega y verificación
Guardar contexto en CONTEXTO_PROYECTO.md y este plan en PLAN.md. Fuentes, dependencias e instrucciones Windows/Python 3.11; sin exe.
Comprobar signos/unidades/equilibrio/torque corrector; solución estable y demostración fallida; convergencia con medio paso; IAE, saturación y anti-windup; demostración gratis, tres intentos, tercer registro; estabilidad durante último segundo y caída; pistas y espera no bloqueante; reinicio; ranking ausente/dañado/empates; revisión visual Windows.

Los parámetros aprobados se mantienen comunes a todas las partidas. Cualquier ajuste necesario de validación debe documentarse; los resultados de diferentes configuraciones no se mezclarán.

## Revisión de interfaz solicitada posteriormente
Esta revisión sustituye la distribución y presentación iniciales; mantiene la física y la evaluación aprobadas.
- Paleta de la referencia CSS adjunta: marino/azul/verde lima, salida cian; tipografía Bahnschrift y diseño de escenario mecánico.
- Una gráfica principal grande muestra siempre el recorrido completo con escala fija. Referencia, tolerancia, ventana de evaluación y empujón tienen marcas diferenciadas; no hay zoom ni gráficos secundarios.
- Franja horizontal de ganancias con cifras grandes; tira visual de intentos e IAE; instrumentos separados de las recomendaciones.
- Reproducción 0.25× predeterminada (24 s visibles + 0.65 s de preparación), seleccionable 0.5×/1× y pausa. La prueba física dura 6 s y se evalúa en [5, 6] s; el horizonte distinto obliga a cambiar el identificador del desafío.
- Pantalla de análisis después de cada intento (mínimo 3 s) con IAE destacado, comparación, área de error, ganancias y consejo si falla. El tercero se guarda al completar su reproducción y pasa al ranking mediante botón tras el análisis.
- Verificar legibilidad de campos de ganancias, ausencia de solapamiento a 1120×800, temporización/pausa, referencia y escalas, persistencia exclusiva del tercero y capturas. Quitar el rótulo visible del estado «En espera» y todo texto interno del lienzo del péndulo que compita con la telemetría.


## Revisión de ecuaciones y ampliación solicitadas

La prueba se amplía de 3 s a 6 s para que la demostración y cada intento permitan observar más dinámica; el mismo cambio extiende el IAE y lleva la ventana de estabilidad a [5, 6] s. Se cambia `CHALLENGE` y se archiva el ranking anterior si existe, porque sus IAE no son comparables. `MODELADO_PID.md` documenta la derivación de Lagrange, energía, linealización y polos, Routh–Hurwitz (incluido el caso Ki=0), filtro, Euler del integrador, RK4 de planta, retención de torque, anti-windup, IAE y límites de interpretación.

La gráfica usa el área de trabajo para una sola curva amplia de recorrido completo y permanece en esa escala durante toda la prueba. Se eliminan el rótulo «EN ESPERA» y los textos de escena que invadían la telemetría. La ventana mínima queda en 1120×800 para evitar comprimir la curva y controles.


## Ajuste visual y explicación solicitados

Se alarga solo el dibujo de la varilla durante el juego (factor 1,4 acotado al lienzo). Se elimina botón/estado de zoom y se mantiene únicamente la vista global. Explicar la idealización de planta y controlador, y el empujón como salto de velocidad/impulso angular con derivación. Verificar geometría visual y flujo completo.

## Revisión visual posterior (2026-11-03)

Completado: instalar las cinco skills solicitadas, revisar el estado visual, actualizar jerarquía y paleta, mejorar la lectura de gráfica y ranking, capturar comparación y ejecutar pruebas. Se conservan la planta y reglas vigentes. Detalles y evaluación en DISENO_UI.md.

## Ajuste posterior solicitado

Implementado: entradas editables por teclado, horizonte físico de 10 s, ventana de estabilidad del último segundo, separación de rankings y diseño con menos recuadros.

## Revisión arcade posterior

Completado: simplificar textos, corregir la distribución de telemetría y enriquecer la apariencia del péndulo según la dirección arcade escogida por el usuario.

## Movimiento arcade

Completado: respuesta animada de botones y entrada escalonada del análisis. La verificación incluye interacción con ratón y teclado, estados deshabilitados y animación sin cambio de resultados.

## Actualización vigente

El plan de carro fue cancelado. La versión actual mantiene el pivote e incorpora un motor DC y un escalón 0°→8° a los 4 s. Consultar MODELADO_PID.md para el modelo y README.md para el uso; los planes previos son históricos.
