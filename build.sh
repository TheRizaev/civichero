#!/usr/bin/env bash
# Запуск через supervisor

exec supervisord -c supervisord.conf
