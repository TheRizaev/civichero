#!/usr/bin/env bash
# Launch Django and Telegeam bot together

python telegram_bot.py &

gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
