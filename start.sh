#!/usr/bin/env bash
# Запуск Django и Telegram бота вместе

# Запускаем бота в фоне
python telegram_bot.py &

# Запускаем Django (на переднем плане)
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
