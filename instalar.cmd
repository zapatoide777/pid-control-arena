@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto dependencias
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv
) else (
    python --version >nul 2>&1
    if errorlevel 1 goto falta_python
    python -m venv .venv
)
if errorlevel 1 goto error
:dependencias
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
cscript //nologo "%~dp0crear_acceso_directo.vbs" /silencioso
if errorlevel 1 goto error
echo.
echo Instalacion completa. Abre Juego PID desde el escritorio.
pause
exit /b 0
:falta_python
echo Instala Python 3.11 o posterior desde https://www.python.org/downloads/windows/
echo Activa la opcion Add Python to PATH y vuelve a ejecutar instalar.cmd.
pause
exit /b 1
:error
echo.
echo No se pudo completar la instalacion. Revisa el mensaje anterior y vuelve a intentarlo.
pause
exit /b 1
