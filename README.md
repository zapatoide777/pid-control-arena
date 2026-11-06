# PID / Control Arena

Juego en español para ajustar un PID en un péndulo invertido con motor DC en el pivote. En Windows con Python 3.11, abre `jugar.vbs` para iniciar en pantalla completa sin consola. `jugar.cmd` también inicia el juego y cierra su consola. Pulsa F11 para alternar entre pantalla completa y ventana maximizada, o Alt+F4 para salir.

## Instalación en Windows

1. Descarga el repositorio y extrae el ZIP en una carpeta permanente.
2. Instala Python 3.11 o posterior y activa **Add Python to PATH**.
3. Haz doble clic en `instalar.cmd`. Necesita conexión a Internet para instalar las dependencias.
4. Abre **Juego PID** desde el escritorio: arranca en pantalla completa, sin consola ni barra de título.

El instalador crea un entorno `.venv` dentro del juego y un acceso directo para el usuario actual; no requiere permisos de administrador. Las rutas se calculan desde la carpeta descargada y admiten espacios y tildes.

Si ya tienes las dependencias, puedes crear el acceso directo con doble clic en `crear_acceso_directo.vbs`. Si mueves la carpeta del juego, ejecuta ese archivo de nuevo para actualizarlo. El acceso directo necesita que conserves la carpeta del juego.

**F11** alterna entre pantalla completa y ventana maximizada; **Alt+F4** cierra el juego.

Para instalar o ejecutar desde una terminal, y después crear el acceso directo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cscript //nologo crear_acceso_directo.vbs /silencioso
.\.venv\Scripts\python.exe main.py
```

La demostración no consume intentos. Ajusta Kp, Ki y Kd en los campos o deslizadores y realiza tres pruebas; solo la tercera entra al ranking. La reproducción comienza a 1× y también ofrece 0,5× y pausa. El cálculo físico dura 10 segundos independientemente de la velocidad visual.

El empujón inicial es una velocidad de 2 rad/s. La referencia cambia de 0° a 8° en el segundo 4. La caída se marca a ±90°, pero la simulación continúa. Para el éxito educativo, el error debe permanecer en ±5° durante todo el intervalo de 9 a 10 s y no haber caído. El puntaje es el IAE del error angular, en grados·segundo; menor es mejor. El ranking se separa de versiones anteriores del desafío.

El motor incluye resistencia, inductancia, fuerza contraelectromotriz y límites de tensión y corriente; el pivote incluye fricción viscosa y seca suavizada. Son parámetros educativos hipotéticos, no una representación calibrada de hardware. [MODELADO_PID.md](MODELADO_PID.md) explica ecuaciones, unidades y límites.

Para ejecutar las comprobaciones:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.cache\pytest
```

El ranking se guarda localmente en `data/ranking.json`; un archivo incompatible o dañado se conserva con sufijo `.backup-...` antes de crear otro.

## Editar los textos

Los textos de la interfaz viven en `pid_game/textos_es.json`, organizados en las secciones `menu`, `game`, `report`, `hints`, `guide` y `ranking`. Cada valor final debe ser una cadena JSON. El código los obtiene mediante claves con puntos, por ejemplo `game.attempt` o `guide.kp.title`.

Las plantillas usan marcadores con nombre entre llaves y conservan el formato numérico indicado. Al editar una frase, no borres, renombres ni cambies los marcadores: `game.attempt` usa `{numero}`, `game.playback` usa `{duracion}` y `{velocidad}`, `report.best_attempt` usa `{numero}` y `{estado}`, y `ranking.result` usa `{iae}`, `{puesto}` y `{total}`. La lista completa está declarada en `pid_game/textos.py`; el validador comprueba que los marcadores coincidan con ella.

Guarda el archivo como UTF-8; también se admite el BOM UTF-8 que algunos editores agregan. La aplicación valida el catálogo antes de abrir la interfaz. Si el JSON tiene un error de sintaxis, el mensaje identifica el archivo, la línea y la columna. Los marcadores inválidos o incompatibles también producen un mensaje breve con la clave afectada.
