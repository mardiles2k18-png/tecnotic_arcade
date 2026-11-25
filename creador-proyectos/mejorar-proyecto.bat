@echo off
rem Arrastra la carpeta de un proyecto sobre este archivo (o haz doble clic y escribe la ruta).
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
if "%~1"=="" (%PY% generador.py --mejorar-preguntar) else (%PY% generador.py --mejorar "%~1")
pause
