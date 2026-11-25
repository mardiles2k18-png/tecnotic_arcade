@echo off
rem Vuelve a configurar Graphify en este proyecto (por si no se pudo al crearlo).
cd /d "%~dp0"
where graphify >nul 2>nul || pip install --user graphifyy
graphify install
graphify install --platform codex
graphify claude install
graphify codex install
echo.
echo Listo. Ahora en Claude escribe /graphify .   o en Codex $graphify .
pause
