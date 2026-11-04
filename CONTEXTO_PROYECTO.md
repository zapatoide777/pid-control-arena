# Contexto del proyecto

## Objetivo y decisiones acordadas
- Juego introductorio de sintonización PID, Python, escritorio Windows, interfaz en español.
- Péndulo invertido idealizado con torque en pivote; no péndulo sobre carro.
- Referencia 0°, empujón idéntico por velocidad angular inicial vigente de 2 rad/s.
- Tres estados: en espera, jugando y juego terminado. Fases internas para demostración, edición, ejecución y devolución.
- Demostración mala al comenzar cada partida, sin consumir intentos; omisible tras verla una vez en la sesión.
- Tres sintonizaciones fijas durante cada prueba. Solo la tercera se guarda y puntúa.
- Prueba de 6 s; éxito solo sin caída y dentro de ±5° durante TODO el intervalo [5, 6] s.
- Caída al alcanzar ±90°; continuar simulación y error sin envolver el ángulo.
- Resultado IAE en grados·segundo sobre [0, 6], menor es mejor. Ranking exclusivamente por IAE, incluso con caídas.
- Pistas contextuales solo tras fallos. Espera mínima 3 s tras intentos fallidos 1/2; continuar mediante botón.
- Pantalla final: tabla y gráfico de diez mejores resultados históricos; resaltar actual aun fuera del top diez.
- Parámetros, límites y verificaciones detallados en PLAN.md. Entregar fuentes e instrucciones; sin exe en v1.

## Fundamento y fuentes
El balance de momentos de la planta elegida se deriva directamente: J θ'' = m g l sin(θ) − b θ' + u. θ=0 es la vertical superior; θ positivo horario; torque positivo aumenta θ. Esta planta tiene actuación ideal directa, distinta al carro-péndulo de CTMS.

Referencia consultada durante planificación para comparar opciones: University of Michigan, CTMS, Inverted Pendulum, https://ctms.engin.umich.edu/CTMS/index.php?example=InvertedPendulum&section=ControlPID . No se reutilizan las ecuaciones ni las ganancias del sistema sobre carro.

## Estado
Implementación completada y validada: aplicación PySide6, núcleo independiente de Qt, ranking JSON y lanzador jugar.cmd. Python 3.11.15; PySide6 6.12.0; pytest 9.2.0, fijados en dependencias.

Las cifras registradas en la primera versión correspondían a horizonte de 3 s y dejaron de ser comparables al ampliarse el reto. La medición vigente T6 se consigna más abajo y en VERIFICACION.md.

Se mantienen m, l, J, b, g, ganancias máximas, torque y algoritmo. El horizonte se amplía en la revisión actual y por eso el ranking está versionado para no mezclar desafíos. La derivada usa medición ideal de velocidad, filtrada; el anti-windup es condicional. La omisión de demostración se habilita tras verla una vez por sesión. Fecha de registros según zona local del equipo. El resultado actual se identifica con texto y color para garantizar legibilidad en Windows.

Documentación de uso y modelo: README.md. Evidencia numérica, pruebas y revisión visual: VERIFICACION.md. Capturas en artifacts/screenshots; son fixtures separados del ranking real. Historial operativo en .agent/progress.md.

## Revisión visual solicitada y completada
Nueva identidad PID / Control Arena: marino #101c38, azul #326eab, verde #a1d65a y cian #57d5f3, inspirada en la imagen CSS que adjuntó el usuario. Fuente Bahnschrift para títulos/cifras, Segoe UI para cuerpo. No se usa logo institucional.

Distribución renovada: gráfica protagonista a la izquierda, instrumento mecánico con estela a la derecha, tira de tres intentos con sus IAE arriba y controles PID horizontales abajo. Campos numéricos grandes y legibles aun deshabilitados; corregida interacción Qt/QSS que reducía el editor a 1 px. Ventana mínima vigente 1120×800 lógicos.

La reproducción ahora es 0.25× por defecto: 6 s físicos toman 24 s visibles, más 0.65 s de preparación. La gráfica única muestra siempre el recorrido completo con escala fija; referencia verde, salida cian y marcas de tolerancia, empujón y ventana evaluada.

Después de TODOS los intentos se abre un análisis de al menos 3 s, con IAE grande, diferencia frente al anterior, miniatura del área de error, lectura de ganancias y pista solo si falla. Tras el tercero se guarda inmediatamente el resultado y se permite abrir el ranking desde el análisis. Es una fase de presentación: se mantienen exactamente los tres estados principales de Game.

Las pruebas de UI cubren pausa, escala, reloj/velocidad, campos legibles y ausencia de solapamiento a 1120×800. Capturas del juego y análisis en tamaños normal y mínimo.


## Ampliación T6 previa: empujón 1 rad/s (2026-11-02)

Se extiende el horizonte físico de 3 s a **6 s** para mostrar más recorrido en la demostración y en cada intento. Se conservan referencia 0°, empujón inicial `ω(0)=1 rad/s`, modelo, PID, límite de torque, resolución y paso de 1 ms. La evaluación de estabilidad se actualiza coherentemente al último segundo `[5,6]`; el IAE cubre `[0,6]`. `CHALLENGE` pasa a `pivot-v2-…-T6-…`; cualquier ranking T3 se preserva mediante backup y no se mezcla.

La revisión independiente de dos subagentes confirmó los signos y unidades del balance dinámico y del PID, la compatibilidad de `J` con una barra uniforme de 0,6 m, el carácter inestable de la vertical superior y las condiciones locales de Routh–Hurwitz. La nota [MODELADO_PID.md](MODELADO_PID.md) contiene la derivación y las salvedades: derivada filtrada sobre medición, anti-windup condicional, integral Euler explícita, filtro exponencial y RK4 aplicado solo a la planta con torque retenido.

Se eliminó el rótulo visible «EN ESPERA» y el texto dibujado dentro del lienzo del péndulo que se cruzaba con la telemetría. El espacio de gráficas se dedica a una sola curva grande en recorrido completo, sin control de zoom. Una sola leyenda identifica salida, referencia, banda y empujón. La ventana mínima es 1120×800 para prevenir compresión y superposición.

Mediciones del modelo T6: demostración `Kp=0,1; Ki=0; Kd=0`: cae, IAE 812,647866 °·s, máximo 228,11°. Controlador interno de verificación `2; 0,2; 0,4`: estable, IAE 1,338713 °·s, máximo 2,82°. Solo el tercer intento de una partida se registra.


## Ajuste de escala gráfica solicitado (2026-11-02)

En el panel activo, la longitud ilustrada de la varilla se escala por 1,4 con un límite para que masa, rueda y base quepan en el lienzo; la escena inicial conserva su tamaño. La geometría física `l=0,3 m` y todas las señales simuladas permanecen sin cambios. Se quitó el botón «Ver detalle ±8°» y la lógica de zoom; la única gráfica permanece en recorrido completo por prueba. El impulso se resalta con marcador coral. Teoría respondida/documentada: el péndulo tiene gravedad no lineal pero actuador/sensor ideales; `ω(0+)−ω(0−)=1 rad/s` equivale a impulso angular `JΔω=0,024 N·m·s`, aplicado en la simulación como condición inicial, no fuerza finita. Se explica por qué el PID se comporta tan bien dentro de las idealizaciones. Suite final 33 passed; UI Windows 5 passed.


## Ajuste del empujón vigente (2026-11-02)

Se elevó la velocidad angular inicial de 1 a **2 rad/s** en todas las demostraciones e intentos. Equivale a 115°/s en el pivote y a 0,6 m/s en el centro de masa (l=0,3 m). Desde reposo, el impulso angular equivalente se duplica de 0,024 a **0,048 N·m·s**. El integrador inicia con `θ=0`, `ω=2`; no se agregó una fuerza finita ni cambió el setpoint. Escaneo con el controlador 2/0,2/0,4: sin caída, cumple la ventana final, pico 5,64° e IAE 2,676824 °·s. Demostración mantiene falla (pico 229,74°, IAE 833,135567 °·s). El identificador cambia de `pivot-v2-…-w1-T6…` a `pivot-v3-…-w2-T6…`, de modo que los rankings de perturbaciones distintas se archivan y no se mezclan.

## Revisión visual (2026-11-03)

Se instalaron cinco skills de diseño, capturas, evaluación e ilustración y se actualizó la interfaz hacia fondos claros, azul marino y verde, con gráfica de mayor legibilidad y mecanismo de base facetada. Los detalles y límites de la evaluación visual constan en DISENO_UI.md. El gráfico de ranking utiliza log₁₀(1 + IAE) ante valores extremos, únicamente como transformación visual; los datos y su orden se conservan. Las decisiones visuales anteriores quedan como historial.

## Prueba de 10 s y revisión de controles (2026-11-03)

La duración física aumenta a 10 s, con evaluación en [9,10] s y 10001 muestras. El ranking T6 se conserva como respaldo y no se mezcla con el T10. Se corrigió la edición de ganancias por teclado y se redujeron paneles y mayúsculas; se usa Segoe UI. La demo cae (IAE 1447,935714 °·s); 2/0,2/0,4 estabiliza (IAE 3,064944 °·s).

## Dirección arcade y telemetría (2026-11-03)

A petición del usuario, la presentación cambia a una dirección arcade tecnológica oscura con verde y azul, menos texto y péndulo dibujado con luz, sombras y piezas metálicas. Es una ilustración 2D con apariencia de volumen, no una simulación 3D. Ángulo y tiempo se muestran en columnas separadas y el tiempo total en su etiqueta. La planta, controlador, horizonte y ranking no cambian.

## Animaciones arcade (2026-11-03)

El usuario eligió animación arcade marcada. Los botones animan brillo al pasar el cursor y oscurecimiento al pulsar; el informe muestra IAE y pista de forma escalonada y una línea luminosa recorre la cabecera. Las animaciones son visuales, usan el event loop de Qt y no afectan el cálculo, tiempo físico, espera ni ranking.

## Pulido visual completo (2026-11-03)

La guía vigente es `GUIA_VISUAL.md`; se consolidó en `DISENO_UI.md` qué secciones son históricas y cuáles corresponden al diseño actual. La interfaz usa IBM Plex Sans, IBM Plex Sans Condensed e IBM Plex Mono locales con licencias OFL, y controles de ganancia con campo numérico y deslizador. Se quitaron las cajas de texto y el scroll de la pista; durante la partida, ángulo y tiempo se leen en dos columnas y el IAE va debajo. El informe prioriza IAE y una pista breve. Se corrigió el diagnóstico para decir que el péndulo cayó solo cuando se registró caída.

Botones e informe tienen respuesta visual, respetan `ReducedMotion`, y no alteran el estado ni las métricas. En el equipo de revisión Qt reporta la preferencia de movimiento reducido activa. Para inspeccionar fotogramas intermedios sin tocar la configuración del sistema, `tools/verify_fullscreen.py --full-motion-preview` fuerza movimiento solo en el proceso QA. Las capturas maximizadas están en `artifacts/pantalla-completa/`; cada pantalla reportó 1280×649 e `isMaximized=True`. Suite completa al cierre: 49 aprobadas. Se mantuvieron sin cambios planta, PID, puntaje y reglas de partida.

## Actualización vigente: motor DC directo

El plan de carro fue cancelado. La planta vigente es el péndulo en el pivote con motor DC, fricción suavizada, perturbación inicial de 2 rad/s y referencia 0°→8° en t=4 s. Véanse README.md y MODELADO_PID.md; las secciones anteriores pueden describir versiones históricas. El ranking tiene identificador propio y conserva los datos incompatibles como respaldo.
