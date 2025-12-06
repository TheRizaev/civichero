#!/usr/bin/env bash
python telegram_bot.py &
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
