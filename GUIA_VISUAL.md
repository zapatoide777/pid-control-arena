# Guía visual · PID / Control Arena

## Dirección

Arcade de instrumentos: interfaz oscura, clara a primera vista y con energía contenida. La mecánica se presenta casi frontal, con volumen moderado y una unión motor-eje-varilla fácil de seguir. La escena ilustra el modelo de la aplicación; no altera su física.

## Jerarquía y composición

- Cada pantalla tiene un mensaje principal y una acción dominante.
- Agrupar con alineación y espacio; usar reglas finas para separar secciones. No añadir contenedores decorativos ni slogans.
- Durante la prueba, la curva y el péndulo son los protagonistas. Ángulo y tiempo ocupan posiciones independientes.
- El informe prioriza el IAE y después una recomendación breve y accionable.
- Las ganancias son editables por teclado y deslizador; el valor numérico nunca se oculta.

## Tipografía

- IBM Plex Sans: lectura y controles.
- IBM Plex Sans Condensed: títulos y rótulos de instrumento.
- IBM Plex Mono: tiempo, ángulo, IAE y ganancias cambiantes.
- Mantener jerarquía por tamaño y peso; los datos numéricos usan anchura estable.

## Color y forma

- Fondo marino profundo; azul pizarra para zonas de gráfica.
- Cian para salida/telemetría, verde lima para referencia/acción/estado favorable y coral para la perturbación.
- Combinar color con rótulo, forma o posición. No codificar estados solo con color.
- Bordes en campos y controles editables; superficies de texto ligeras y sin tarjetas repetidas.

## Movimiento

- Movimiento marcado en transiciones poco frecuentes y discreto en acciones repetidas.
- Feedback inmediato en hover, foco y pulsación; el teclado y la activación no esperan a la animación.
- Animar opacidad, brillo y trazos. No desplazar la composición ni ocultar información.
- Respetar la preferencia de movimiento del sistema; todas las pantallas deben seguir completas si la animación se reduce.

## Revisión

- Capturas de la aplicación real, siempre maximizada, con los mismos datos para comparar iteraciones.
- Revisar inicio, demostración, ajuste, ejecución, recomendación, informe final y ranking.
- Inspeccionar los fotogramas de transición, los valores largos, los acentos españoles y los símbolos `θ`, `±`, `°` y `·`.
- Confirmar ensamblaje despejado del motor en `0°`, `±90°` y `180°`.
