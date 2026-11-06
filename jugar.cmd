@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv\Scripts\pythonw.exe"
if not exist "%PY%" (
    echo Ejecuta instalar.cmd antes de abrir el juego.
    pause
    exit /b 1
)
start "" "%PY%" "%~dp0main.py"
exit /b
