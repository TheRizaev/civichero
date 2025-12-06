#!/usr/bin/env bash
# exit on error
set -o errexit
python telegram_bot.py &

# Запускаем Django (на переднем плане)
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
