@echo off
rem Doble clic para crear un proyecto nuevo de Claude + Codex.
cd /d "%~dp0"
where py >nul 2>nul && (py -3 nuevo_proyecto.py %*) || (python nuevo_proyecto.py %*)
pause
