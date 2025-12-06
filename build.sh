#!/usr/bin/env bash
pip install -r requirements.txt
python telegram_bot.py &
gunicorn config.wsgi:application
