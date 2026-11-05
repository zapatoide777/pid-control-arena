@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=..\Juego PID main\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Falta el entorno Python. Sigue los pasos de instalacion de README.md.
    pause
    exit /b 1
)
"%PY%" main.py
if errorlevel 1 pause
