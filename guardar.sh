#!/bin/sh
cd "$(dirname "$0")" || exit 1
git add -A
git commit -m "Respaldo $(date '+%Y-%m-%d %H:%M')"
git pull --no-rebase
git push
