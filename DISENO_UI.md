# Revisión visual de la interfaz

La sección final **“Revisión completa maximizada”** describe el diseño vigente. El resto del archivo conserva las decisiones de iteraciones anteriores; algunas capturas, fuentes y colores allí mencionados ya no corresponden a la versión actual.

La imagen conceptual generada durante la revisión sirvió como referencia de colores y aspecto de instrumento. Representa un carro-péndulo y no describe la planta del juego: el modelo continúa siendo un péndulo accionado en el pivote. La base del dibujo incorpora caras geométricas inspiradas en ilustración isométrica, adaptadas a la representación frontal de la simulación.

Se aplicaron las cinco skills instaladas: diseño mediante especificación, referencia de identidad, capturas de progreso, evaluación por criterios e ilustración isométrica adaptada al componente Qt. Las capturas están en `artifacts/screenshots/`; `artifacts/ui-comparacion.png` compara el mismo estado compacto antes y después. Son renderizaciones Qt fuera de pantalla, no una grabación de la interacción.

## Autoevaluación orientativa

Evaluación propia sobre el mismo estado compacto, sin evaluación independiente ni objetivo numérico solicitado; cada criterio vale 0–2.

| Criterio | Antes | Después | Observación |
|---|---:|---:|---|
| Jerarquía de información | 1 | 1,5 | Menos títulos y énfasis repetidos. |
| Lectura de la gráfica | 1 | 1,5 | Contraste y etiqueta de cero más claros. |
| Identidad visual | 0,5 | 1 | Paleta coherente y mecanismo de geometría más sobria. |
| Tipografía y texto | 1 | 1,5 | Menos mayúsculas y lenguaje más directo. |
| Controles y métricas | 1,5 | 1,5 | Datos visibles; algunos textos siguen pequeños en tamaño mínimo. |
| Total | 5 | 7 | Valoración subjetiva para orientar futuras revisiones. |

El gráfico de clasificación cambia a log₁₀(1 + IAE) cuando hay valores extremos; la tabla muestra el IAE original. Queda pendiente comprobar la experiencia en sesiones reales con jugadores y escalados de pantalla variados. Las capturas estáticas no prueban por sí solas la fluidez de la animación. No se modificaron la física, la evaluación ni el orden del ranking.

## Revisión posterior

Se reemplazó Bahnschrift por Segoe UI, se eliminaron fondos y bordes de las tarjetas y los intentos se presentan con líneas. La reproducción y el análisis se verifican con capturas Qt; el nuevo horizonte es de 10 s. La autoevaluación anterior corresponde a la iteración anterior.

## Dirección arcade tecnológica

La revisión posterior usa un fondo marino oscuro y acentos luminosos azul y verde. El péndulo conserva su pivote frontal y añade capas, reflejos y sombras dibujadas en Qt para dar profundidad. La visual es 2D con apariencia de volumen; no modifica el modelo físico. Se redujo el texto y se reservaron columnas para las métricas; capturas en `artifacts/screenshots/caida-2410.png` y `01-inicio.png`.

## Animación arcade

Los botones añaden un borde luminoso al pasar el cursor y responden al pulsar; la pantalla de análisis revela el IAE y luego la pista con opacidad, mientras una línea luminosa recorre la cabecera. Los tiempos de entrada son inferiores a la espera existente y no bloquean el event loop. `artifacts/animacion/transicion.png` y `botones.png` son capturas Qt preparadas, no grabaciones.

## Dirección de detalle: arcade de instrumentos

Decisión del jugador: números grandes, líneas finas y acentos luminosos, con animación marcada en transiciones y controles sin mover la geometría de lectura. La fuente Bahnschrift se usa en títulos y cifras cuando está disponible en Windows; Segoe UI mantiene legibilidad en texto y unidades. Los rótulos deben responder a una acción o estado; las pistas presentan un síntoma y una sugerencia breve, nunca una promesa de estabilidad.

El marcador separa número de intento, estado e IAE sin tarjetas; el intento destacado enciende su línea al aparecer. La barra de texto usa pista redondeada y elimina controles cuadrados. Una única recomendación prioriza oscilación, saturación o caída según las señales observadas; las recomendaciones siguen siendo orientativas.

Evoluciones propuestas: animar la transición de valores de IAE de forma breve sin alterar el cálculo ni la accesibilidad; introducir respuesta visual al mover cada ganancia y un marcador de saturación durante la prueba. Mantener los efectos fuera del área de lectura y validar cada cambio maximizado, pausado y con teclado.

## Representación del actuador

La vista usa geometría tridimensional dibujada por software: carcasa de motor fija al soporte, eje perpendicular al plano de movimiento, brida y varilla solidaria al eje. Los conductores indican la alimentación; no representan un circuito o sensor simulado. La cámara emplea proyección ortográfica oblicua y las dimensiones son ilustrativas. El mismo componente se usa en inicio y en la partida, con el ángulo tomado de la simulación. Un péndulo rotatorio tipo Furuta mueve un brazo horizontal y tiene un péndulo libre; no se representa aquí porque sería otra planta.

Referencia visual de una instalación de péndulo accionado con motor y encoder: https://www.mdpi.com/2813-6640/3/3/11

## Criterios de revisión visual del péndulo

- Lectura: el ángulo y la referencia comparten el mismo centro y se distinguen en vertical, horizontal y caída, incluso durante la partida maximizada.
- Ensamblaje: motor fijo, eje y unión de la varilla identificables; ningún soporte o cable debe atravesar visualmente la varilla.
- Perspectiva: casi frontal, con profundidad suficiente para identificar la carcasa sin deformar la lectura angular.
- Jerarquía y tamaño: la varilla es la figura principal; el motor se reconoce en el panel de juego y las métricas no se recortan.
- Comportamiento: la vista refleja el mismo ángulo que la muestra, sin interferir con la simulación o el reloj.
- Comprobación: probar pantalla maximizada y ángulos 0°, ±90° y 180°, además de la partida real y texto de telemetría.

Observación: la geometría sigue siendo esquemática y proyectada por software; el objetivo es claridad educativa, no fotorrealismo. La revisión es una evaluación visual, no una garantía de que todos los sistemas de escala de Windows sean iguales.

## Revisión completa maximizada · vigente · 2026-11-03

Se aplicó la identidad **arcade de instrumentos**: fondo marino oscuro, líneas finas, acentos cian/lima, IBM Plex Sans para lectura, IBM Plex Sans Condensed para titulares y IBM Plex Mono para telemetría. Las fuentes y sus licencias OFL están en `assets/fonts/`; no se descargan al ejecutar el juego. La escena del pivote es casi frontal, separa visualmente motor, eje y varilla y no usa conductores rojos o azules.

En la partida, la gráfica ocupa la zona principal; a su lado, el instrumento presenta el ángulo y el tiempo en columnas independientes, con el IAE en una fila propia. Las ganancias mantienen simultáneamente campo numérico y deslizador, y la reproducción inicia a 1× con opción 0,5×. Las pistas son frases cortas, usan el espacio disponible sin barra de desplazamiento y solo se muestran ante fallos. El informe destaca IAE, estado y sugerencia; la tira de intentos separa número, estado y valor.

Los botones responden a foco, cursor y pulsación. El informe revela el dato y la pista y traza una línea de acento sin mover el contenido. La preferencia de movimiento reducido de Qt omite la animación conservando texto, métricas, estados y tiempos de juego. En este equipo se detectó `ReducedMotion`; por eso `tools.verify_fullscreen` admite `--full-motion-preview`, que desactiva esa preferencia únicamente dentro del proceso de captura de QA para inspeccionar fotogramas intermedios. El programa normal continúa respetando la preferencia real del sistema.

La verificación visual de Windows se hizo con `showMaximized()`; el área de captura informada por Qt fue 1280 × 649 y `isMaximized()` fue verdadero en todas las pantallas. Se capturaron y revisaron inicio, demostración, ajuste, intento, fotograma animado, informe estable, resultado y ranking en `artifacts/pantalla-completa/`. No se modificaron modelo, PID, IAE, ganancias ni reglas. La suite completa registra 49 pruebas aprobadas. Estas capturas comprueban distribución y recortes en la resolución disponible; no reemplazan una prueba de uso con jugadores ni garantizan el mismo escalado en todos los monitores.
