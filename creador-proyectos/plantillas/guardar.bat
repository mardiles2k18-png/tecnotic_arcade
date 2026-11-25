@echo off
cd /d "%~dp0"
git add -A
git commit -m "Respaldo %date% %time%"
git pull --no-rebase
git push
pause
