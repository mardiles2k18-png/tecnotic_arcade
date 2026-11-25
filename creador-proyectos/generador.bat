@echo off
rem Doble clic: menú para crear o mejorar un proyecto.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 generador.py %*) else (python generador.py %*)
pause
