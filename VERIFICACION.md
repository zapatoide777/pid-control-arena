# Nota sobre esta verificación

Las mediciones de esta página corresponden a versiones anteriores salvo que se indique lo contrario. Para el modelo vigente con motor DC y referencia escalonada consulta MODELADO_PID.md y ejecuta las pruebas actuales de README.md.

# Verificación del proyecto

> Las secciones anteriores documentan T3 y el primer T6 con empujón de 1 rad/s. La última sección registra el desafío vigente T6 con 2 rad/s. Sus IAE se conservan en rankings versionados y no se mezclan.

Entorno: Windows, Python 3.11.15, PySide6 6.12.0, pytest 9.2.0.

## Simulación y evaluación

Resultados calculados con el núcleo del juego, mismo empujón y horizonte de 3 s:

| Kp / Ki / Kd | IAE, dt=1 ms (°·s) | IAE, dt=0,5 ms (°·s) | Resultado |
|---|---:|---:|---|
| 0,10 / 0 / 0 (demostración) | 378,642005 | 378,655037 | Caída; falla |
| 2 / 0,20 / 0,40 (verificación) | 1,095881 | 1,100206 | Estable; sin caída |
| 10 / 5 / 3 | 0,180351 | 0,186314 | Estable; sin caída |

La máxima diferencia absoluta de IAE al reducir a medio paso en estos casos es 0,0131 °·s. La máxima diferencia de ángulo final es 0,000243 rad. El controlador muestreado y la retención de torque también cambian su período en esa comparación; no se presupone convergencia de orden cuatro del lazo completo.

El máximo ángulo de la demostración es 228,11°, confirmando que la caída se detecta y que el ángulo no se envuelve. La sintonización de verificación alcanza un máximo de 2,82° y cumple la banda durante el último segundo.

Se verifican por pruebas: equilibrio exacto sin perturbación, signo desestabilizante de gravedad y corrector de torque, RK4 contra aceleración constante analítica, integral absoluta sin cancelación, rechazo de excursión fuera de banda en el último segundo, caída seguida de retorno, reinicio reproducible y comportamiento del filtro/anti-windup.

## Flujo, ranking e interfaz

- Demostración sin consumo, omisión solo después de verla y tres intentos exactos.
- Bloqueo de edición durante prueba y conservación de ganancias entre intentos.
- Espera de al menos 3 s tras fallo en intentos 1/2, sin bloquear eventos; sin pistas tras éxito.
- Tercer intento como único resultado persistido; registro idempotente.
- Ranking por IAE, empate estable por orden de inserción, resultado actual fuera del top diez visible en tabla y gráfico.
- Archivo inexistente, JSON dañado, estructura incompatible, valores numéricos enormes y error de escritura con resultado en memoria.
- Demostración reproducida con temporizador real durante 3 s y prueba de flujo completo de interfaz.
- Pistas extensas dentro de un área desplazable y resultado actual visible después de reducir la ventana.

Suite: **30 pruebas aprobadas**. `python -m pip check`: sin dependencias rotas.

Se generaron e inspeccionaron capturas Qt en Windows de inicio, demostración, devolución con espera, control estable, resultado estable y ranking con caída final, tanto a 1280×900 como a 1100×820 píxeles lógicos. También se abrió y capturó una ventana con el plugin nativo `windows`: bucle de eventos y cierre con código 0. Las cuatro pruebas de interfaz se repitieron con `QT_QPA_PLATFORM=windows`: **4 aprobadas en 4,77 s**, incluyendo reloj real, flujo de intentos, ranking fuera del top diez y pista extensa.

Durante la verificación se corrigieron: vida útil de las curvas límite de QAreaSeries (cierre nativo), texto de pistas extenso sin desplazamiento, recuperación de números enormes en JSON dañado y revelado de fila actual al redimensionar. El plugin offscreen no enumeraba fuentes; las capturas cargan las fuentes Segoe UI instaladas cuando hace falta.

Las capturas de `artifacts/screenshots` y sus registros son fixtures de QA, nunca se guardan en `data/ranking.json`. No se requiere hardware real ni se validan motores o sensores físicos.

## Rediseño Control Arena
31 pruebas aprobadas tras el rediseño, incluyendo el núcleo original sin cambios. Cinco pruebas de interfaz ejercitan flujo completo, análisis de cada intento, IAE visible, espera también tras éxito, persistencia del tercero antes de abrir ranking, reproducción en reloj real, zoom, pausa y velocidad lenta.

Un reloj controlado verifica que 0.65 s de preparación + 4 s visibles a 0.25× corresponden exactamente a 1 s físico; pausar 4 s no avanza la señal ni modifica el IAE. Los límites de detalle permanecen en ±8°, la vista completa incluye la caída y la referencia permanece en 0°.

Regresiones visuales cubiertas: editor interno de ganancias >65 px de ancho y alto suficiente para la fuente; escena sin solaparse con telemetría a 1120×800. Inspeccionadas capturas de inicio, control estable, caída/demo, análisis fallido/estable/final y ranking en 1400×940 y 1120×800.

Corregidos durante esta revisión: campos vacíos por NoButtons/QSS, fondo blanco exterior de Qt Charts, glifos de leyenda ausentes y límites de altura del escenario/etiquetas en ventana compacta. Física, horizonte y algoritmo de puntuación sin cambios; el ranking anterior sigue siendo compatible.

Última ejecución del rediseño: suite completa **31 passed in 7.03s**; interfaz con `QT_QPA_PLATFORM=windows`: **5 passed in 6.35s**.


## Primera versión T6, empujón 1 rad/s (histórica)

El horizonte se amplió a 6 s para mostrar más respuesta en cada demostración y prueba. El éxito se evalúa en todas las muestras de `[5,6] s`, la caída sigue marcada en ±90° y la integral continúa hasta el final. El identificador del desafío cambió a `pivot-v2-…-T6-…`; el test de persistencia confirma que un JSON T3 se respalda y no se importa al ranking nuevo.

| Kp / Ki / Kd | IAE 1 ms (°·s) | IAE 0,5 ms (°·s) | Resultado | Pico |
|---|---:|---:|---|---:|
| 0,10 / 0 / 0 (demo) | 812,647866 | 812,747977 | Caída | 228,11° |
| 2 / 0,20 / 0,40 (control de verificación) | 1,338713 | 1,344094 | Estable | 2,82° |
| 10 / 5 / 3 | 0,207767 | 0,214665 | Estable | 0,78° |

La variación máxima observada del IAE al pasar de 1 ms a 0,5 ms en estos tres casos es 0,100111 °·s (demo). Para el controlador de verificación es 0,005382 °·s. Esto es una comparación numérica finita del lazo muestreado: bajar el paso también aumenta la frecuencia de actualización PID, así que no se interpreta como prueba de orden cuatro global.

La interfaz deja una gráfica temporal grande, siempre de recorrido completo y sin botón de detalle. La varilla del péndulo se amplió durante el juego (factor ilustrativo 1,4, limitado al panel); no altera la planta. La salida, el setpoint 0°, banda ±5°, empujón y último segundo evaluado quedan diferenciados. Se retiró el rótulo visible «EN ESPERA» y el texto que se dibujaba dentro del panel del péndulo junto a la telemetría. La ventana mínima 1120×800 se revisó visualmente; el panel de pista ahora queda alineado arriba, resaltado y separado de la lectura de ganancias. Capturas nuevas de los estados inicial, demo, juego, análisis y tamaño mínimo en `artifacts/screenshots/`.

Verificación de esta revisión: suite completa **33 passed en 10,68 s**; pruebas nativas de interfaz **5 passed en 9,71 s** con `QT_QPA_PLATFORM=windows`; `pip check` sin dependencias rotas. La prueba del flujo usa la demo de 6 s y comprueba los tres intentos, reporte y ranking; pruebas visuales verifican la gráfica amplia sin control de zoom, una varilla al menos 25% más larga en juego, la ausencia de texto «EN ESPERA», la telemetría sin solapamiento y la posición del consejo por encima de las ganancias.

El modelo y el controlador se derivan y explican en profundidad en [MODELADO_PID.md](MODELADO_PID.md), incluyendo energía, polos, Routh–Hurwitz, el caso `Ki=0`, filtro exponencial, Euler del integrador y RK4 únicamente sobre la planta con torque retenido.


## Desafío vigente T6, empujón 2 rad/s

Todas las pruebas parten ahora de `θ(0)=0`, `ω(0)=2 rad/s` (115°/s). Desde reposo eso equivale a impulso angular `JΔω=0,048 N·m·s`, aplicado como salto de condición inicial. La velocidad del centro de masa es 0,6 m/s. Este cambio duplica la perturbación; el identificador pasa a `pivot-v3-…-w2-T6…` y respalda automáticamente un ranking T6/w1 incompatible.

| Kp / Ki / Kd | IAE 1 ms (°·s) | IAE 0,5 ms (°·s) | Resultado | Pico |
|---|---:|---:|---|---:|
| 0,10 / 0 / 0 (demo) | 833,135567 | 833,268666 | Caída | 229,74° |
| 2 / 0,20 / 0,40 | 2,676824 | 2,687581 | Estable | 5,64° |
| 10 / 5 / 3 | 0,503589 | 0,517200 | Estable; saturación breve | 1,72° |

Así el empujón se ve con claridad, el controlador base aún cumple el criterio del último segundo y una mala sintonización continúa fallando. Al reducir el paso a 0,5 ms, la diferencia de IAE fue 0,133099 °·s en la demo, 0,010757 en el controlador base y 0,013610 (2,63%) con ganancias máximas; la cadencia del PID también cambia al variar el paso. La última suite completa queda en **34 passed en 10,98 s**; la UI nativa en Windows, **5 passed en 10,25 s**; `pip check` no encontró dependencias rotas.

## Revisión de interfaz (2026-11-03)

Suite completa: 34 pruebas aprobadas. Pruebas de interfaz con plataforma Qt Windows: 5 aprobadas. `python -m tools.verify_ui` generó capturas Qt fuera de pantalla con datos de prueba separados del ranking real. Se revisaron inicio, juego, análisis y clasificación, incluyendo ventana mínima. La comparación visual se encuentra en `artifacts/ui-comparacion.png`. La escala log₁₀(1 + IAE) para valores extremos se verifica con una prueba de interfaz y no modifica los valores registrados. Las capturas estáticas no sustituyen una prueba de uso con jugadores.

## Entrada de ganancias y desafío de 10 s (2026-11-03)

Suite completa: 36 pruebas aprobadas; pruebas de interfaz con Qt Windows: 6 aprobadas. Una prueba escribe Kp, Ki y Kd con eventos reales de teclado, confirma cada campo y verifica las ganancias usadas por el intento. La configuración regional determina el separador decimal. La evaluación comprueba todas las muestras de [9,10] s y se verificó que el ranking T6 anterior se archiva sin mezclarse. Capturas Qt fuera de pantalla en artifacts/screenshots.

## Péndulo y telemetría arcade (2026-11-03)

Pruebas automatizadas: 39 aprobadas; 9 pruebas de interfaz aprobadas con la plataforma Qt de Windows. La geometría de ángulo y tiempo durante una caída se verifica en 1120×800, 1400×940 y 1920×1000: campos separados, textos dentro de sus columnas y debajo del escenario. Se prepararon capturas reales de Qt fuera de pantalla en tres instantes de la caída; no son grabaciones ni pruebas de percepción de movimiento. La ilustración de volumen no altera la simulación.

## Animaciones de interacción (2026-11-03)

Suite completa: 41 pruebas aprobadas; 11 pruebas de interfaz aprobadas con Qt para Windows. Se probaron estados de botón con cursor y pulsación, teclado, deshabilitación, opacidades y línea en diferentes instantes, exactitud del IAE y permanencia de la espera de continuación. Las secuencias de `artifacts/animacion/` son capturas preparadas fuera de pantalla con Qt; no equivalen a un video ni a una evaluación perceptiva con jugadores.

## Pulido visual completo (2026-11-03)

- Suite completa: **49 aprobadas** (`pytest -q`).
- Interfaz: comprobada la pista sin `QScrollArea`, el espacio entre sugerencia y ganancias, telemetría en dos columnas más IAE, entrada por teclado, sincronización campo/deslizador y preferencia de movimiento reducido/animado.
- Pantallas de Windows en modo maximizado: inicio, demo, ajuste, intento, transición de análisis, estado estable, resultado y ranking. Todas las capturas informaron `isMaximized=True` y tamaño 1280×649.
- Se revisó visualmente el fotograma intermedio `pista-animacion.png` con el modo de vista previa QA. Ese modo desactiva la preferencia reducida únicamente en el proceso de captura; la aplicación normal respeta el ajuste del sistema.
- Las capturas están bajo `artifacts/pantalla-completa/`; el ranking QA está aislado y no añade resultados al ranking real.
- No se modificaron planta, controlador, IAE, puntaje o reglas de partida.

