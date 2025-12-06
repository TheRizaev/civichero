import os

# Конфигурация бота
# В продакшене токен берется из переменной окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8455100116:AAG5Joe1slEAQGRNPjZ845Apb_M15P5AanE')

# Порт HTTP сервера (на Render может быть переопределен)
WEBHOOK_PORT = int(os.environ.get('PORT', 8001))
