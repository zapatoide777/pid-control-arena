# Estabilidad del PID y comparación física

## Alcance

El análisis corresponde a la versión experimental: péndulo actuado directamente en el pivote, periodo de control de 1 ms, prueba de 15 s y salto de referencia de 0° a 45° en el segundo 5. Los parámetros son supuestos didácticos, no mediciones de un equipo real. No se modificaron la planta, el controlador ni las reglas.

El archivo `MODELADO_PID.md` conserva una descripción anterior: indica 10 s, un salto a 8° en el segundo 4, un criterio de caída y el tercer intento para el ranking. La implementación actual usa 15 s, un salto a 45° en el segundo 5, dos ventanas de estabilidad y el mejor intento. El código vigente es la referencia para este informe.

## Frontera local

Se linealizó alrededor de cada equilibrio el mapa digital de un paso: actualización exponencial del filtro, integral de Euler, motor eléctrico y planta integrados mediante RK4 con tensión retenida. Los polos deben tener módulo inferior a uno. Se suponen perturbaciones infinitesimales y límites inactivos; el anti-windup, las saturaciones y el seno completo se consideran en los ensayos no lineales. Con Ki=0 se elimina el estado integral inactivo.

Para 0° y **control proporcional puro** (Ki=Kd=0), el intervalo local es aproximadamente **0,5886 < Kp < 33,785**. La ganancia crítica superior se calcula fuera del límite seleccionable de 10, sin modificarlo. El valor continuo aproximado obtenido anteriormente, 34,529, no incluye el muestreo digital del mismo modo. Ninguno es una frontera universal: al cambiar Ki o Kd cambia la estabilidad.

Ejemplos de frontera con Kd fijo y referencia 0° (local, sin saturación):

| Kp | Kd | Ki crítico aproximado |
|---:|---:|---:|
| 0,6 | 0,08 | 0,11618 |
| 1 | 0,08 | 4,14508 |
| 0,6 | 0,5 | 0,19323 |

Estos valores identifican el cruce local del círculo unidad en los intervalos examinados; no implican que todas las demás ganancias o trayectorias sean estables. Para Ki>0 también se analiza el equilibrio de seguimiento de 45°: el integrador aporta aproximadamente −0,416 N·m, con corriente aproximada −1,249 A.

Por ejemplo, con Ki=5 y referencia 0°, la frontera inferior de Kp es aproximadamente 1,086 para Kd=0,08; 0,886 para Kd=0,5; y 0,622 para Kd=3. En el barrido hasta Kp=10 no se detectó una frontera superior para esos cortes. Se muestrearon Ki=0, 1, 2, 3, 4 y 5, por lo que no se garantiza detectar regiones estrechas entre los puntos examinados.

Las curvas y datos reproducibles están en [frontera a 0°](artifacts/analisis_estabilidad/frontera_kp_ki_0deg.svg), [frontera a 45°](artifacts/analisis_estabilidad/frontera_kp_ki_45deg.svg) y [tabla de fronteras](artifacts/analisis_estabilidad/fronteras_kp_ki.csv). En 45°, el seguimiento exacto requiere Ki>0; con Ki=0 el equilibrio puede presentar error estático.

## Simulación completa frente a estabilidad local

Los cruces se cuentan desde el escalón con histéresis de ±1°. El asentamiento es el tiempo posterior al escalón desde el cual el error permanece dentro de ±5° hasta el final. La saturación PID cuenta pasos en que el comando no limitado supera ±2 N·m; la saturación de corriente cuenta muestras que alcanzan ±6 A. El éxito exige las dos ventanas del juego, no solo la estabilidad alrededor de 45°.

| Kp, Ki, Kd | Local 0° | IAE | Cruces | Sobreimpulso | Asentamiento | PID / corriente en límite | Éxito |
|---|---|---:|---:|---:|---:|---|---|
| 0,6; 0,02; 0,08 | Estable, muy próximo al límite | 538,81 | 1 | 64,02° | No | 0 % / 0 % | No |
| 0,6; 0,2; 0,08 | Inestable | 229,78 | 2 | 66,61° | 4,642 s | 0 % / 0 % | No |
| 2; 1; 0,5 | Estable | 44,65 | 1 | 15,71° | 2,991 s | 0 % / 0 % | Sí |
| 2; 5; 0,5 | Estable | 30,30 | 2 | 22,68° | 1,251 s | 0 % / 0 % | Sí |
| 10; 5; 0,5 | Estable | 640,35 | 27 | 86,68° | No | 89,22 % / 9,91 % | No |
| 10; 5; 3 | Estable | 99,89 | 28 | 19,23° | 9,886 s | 81,77 % / 0 % | No |

Por ejemplo, (10, 5, 0,5) tiene radio espectral local 0,999426 en 0° y 0,999438 en 45°, pero falla la maniobra completa. Un polo estable local no garantiza recuperación desde la perturbación y el salto grandes del juego. El resultado de 0,6; 0,2; 0,08 también muestra que permanecer dentro de la banda final no garantiza cumplir la primera ventana. Su radio espectral en 0° es aproximadamente 1,00000484 por muestra: la inestabilidad local es lenta, con un tiempo de crecimiento de alrededor de 207 s, por lo que 15 s no necesariamente la revelan.

## Referencias físicas

El juego utiliza m=0,2 kg, distancia al centro de masa 0,3 m, J=0,024 kg·m², R=2 Ω, L=0,16 H, Kt=0,333 N·m/A, alimentación ±12 V y límite ideal ±6 A. Su constante eléctrica L/R es 80 ms y el par máximo ideal Kt·I es 2 N·m. El modelo no considera calentamiento ni distingue entre capacidad continua y de corta duración.

| Dato | Juego | Referencia publicada | Límite de la comparación |
|---|---:|---:|---|
| Masa y longitud | 0,2 kg; centro de masa a 0,3 m | Quanser QNET: eslabón 0,024 kg; largo 0,129 m | Son dimensiones distintas; el largo del eslabón no es la distancia a su centro de masa. |
| Motor: Kt y R | 0,333 N·m/A; 2 Ω | Quanser QNET: 0,042 N·m/A; 8,4 Ω | Su motor acciona un brazo horizontal; el péndulo gira libre en otro eje. No puede sustituirse directamente en este modelo. |
| Corriente | 6 A, límite ideal | Quanser QNET: amplificador 0,5 A continua; 2,5 A pico | El juego no modela la duración admisible ni temperatura. |
| R, L y constante eléctrica | 2 Ω; 160 mH; 80 ms | Maxon RE 13, 12 V: 28 Ω; 0,579 mH; L/R ≈ 0,0207 ms | Es un motor pequeño de 1,5 W; sus cifras no prueban que el motor supuesto del juego sea imposible ni bastan para reemplazarlo. |

Fuentes primarias: [especificaciones Quanser QNET 2.0](https://www.quanser.com/products/qnet-2-0-rotary-pendulum-board/), [ficha Maxon RE 13](https://www.maxongroup.com/maxon/view/product/motor/dcmotor/re/re13/118531). Un [prototipo de péndulo con rueda de reacción](https://www.frontiersin.org/journals/control-engineering/articles/10.3389/fcteg.2026.1905949/full) aporta datos experimentales, pero la rueda intercambia momento con el péndulo y añade estados; no equivale a un motor externo fijo en el pivote.

## Recomendación

Antes de cambiar ganancias o física, seleccionar un motor y una geometría de accionamiento directo con parámetros verificables, en particular resistencia, inductancia, Kt, corriente continua y pico, e inercia y fricción del conjunto. Comparar la respuesta de ese conjunto con el juego bajo la misma perturbación. La inductancia de 160 mH y la corriente ideal de 6 A son parámetros prioritarios para revisar, pero las fuentes anteriores no justifican reemplazarlos por sus valores: describen motores y mecanismos diferentes.
