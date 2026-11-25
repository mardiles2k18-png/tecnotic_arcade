@echo off
rem Doble clic para crear un proyecto nuevo.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% generador.py --crear %*
pause
