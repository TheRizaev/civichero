#!/usr/bin/env bash
# Запуск Django и Telegram бота вместе

python telegram_bot.py &

gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
