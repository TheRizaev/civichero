import asyncio
import os
import sys
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Добавляем путь к Django проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from dispatcher.models import Doctor, Call
from django.utils import timezone as django_timezone
from asgiref.sync import sync_to_async


# Конфигурация
BOT_TOKEN = "8455100116:AAG5Joe1slEAQGRNPjZ845Apb_M15P5AanE"  # Замените на ваш токен

# Инициализация
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_phone = State()


# Состояния для вызова
class CallStates(StatesGroup):
    waiting_for_report_photo = State()
    on_call = State()


# Функция расчета расстояния между координатами
def calculate_distance(lat1, lon1, lat2, lon2):
    """Рассчитать расстояние между двумя точками по формуле Haversine (в км)"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return round(km, 2)


# ==================== ASYNC ФУНКЦИИ ДЛЯ РАБОТЫ С БД ====================

@sync_to_async
def get_doctor_by_telegram_id(telegram_id):
    """Получить врача по telegram_id"""
    try:
        return Doctor.objects.get(telegram_id=telegram_id)
    except Doctor.DoesNotExist:
        return None


@sync_to_async
def doctor_exists(telegram_id):
    """Проверить существование врача"""
    return Doctor.objects.filter(telegram_id=telegram_id).exists()


@sync_to_async
def create_doctor(telegram_id, first_name, last_name, phone):
    """Создать нового врача"""
    return Doctor.objects.create(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        phone=phone
    )


@sync_to_async
def toggle_doctor_status(telegram_id):
    """Переключить статус онлайн врача"""
    doctor = Doctor.objects.get(telegram_id=telegram_id)
    doctor.is_online = not doctor.is_online
    doctor.save()
    return doctor


@sync_to_async
def update_doctor_location(telegram_id, latitude, longitude):
    """Обновить местоположение врача"""
    doctor = Doctor.objects.get(telegram_id=telegram_id)
    doctor.latitude = latitude
    doctor.longitude = longitude
    doctor.save()
    return doctor


@sync_to_async
def get_call_by_id(call_id):
    """Получить вызов по ID"""
    try:
        return Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        return None


@sync_to_async
def get_online_doctors_list():
    """Получить список онлайн врачей"""
    return list(Doctor.objects.filter(is_online=True))


@sync_to_async
def accept_call_db(call_id, doctor_telegram_id):
    """Принять вызов"""
    try:
        call = Call.objects.get(id=call_id)
        doctor = Doctor.objects.get(telegram_id=doctor_telegram_id)
        
        if call.status not in ['created', 'sent_to_doctors']:
            return None, "Этот вызов уже принят другим врачом"
        
        call.assigned_doctor = doctor
        call.status = 'accepted'
        call.accepted_at = django_timezone.now()
        call.save()
        return call, None
    except Exception as e:
        return None, str(e)


@sync_to_async
def update_call_on_site(call_id):
    """Обновить статус: врач на месте"""
    call = Call.objects.get(id=call_id)
    call.status = 'on_site'
    call.on_site_at = django_timezone.now()
    call.save()
    return call


@sync_to_async
def call_ambulance_db(call_id):
    """Вызвать бригаду"""
    call = Call.objects.get(id=call_id)
    call.ambulance_called = True
    call.ambulance_called_at = django_timezone.now()
    call.save()
    return call


@sync_to_async
def complete_call_db(call_id):
    """Завершить вызов"""
    call = Call.objects.get(id=call_id)
    call.status = 'completed'
    call.completed_at = django_timezone.now()
    call.save()
    return call


@sync_to_async
def get_doctor_statistics(telegram_id):
    """Получить статистику врача"""
    doctor = Doctor.objects.get(telegram_id=telegram_id)
    completed_calls_count = Call.objects.filter(
        assigned_doctor=doctor,
        status='completed'
    ).count()
    return doctor, completed_calls_count


@sync_to_async
def create_test_call_db():
    """Создать тестовый вызов"""
    return Call.objects.create(
        patient_name="Тестовый Пациент",
        patient_age=45,
        patient_gender="male",
        illness_description="Высокое давление",
        address="ул. Тестовая, 123",
        latitude=41.2995,
        longitude=69.2401,
        threat_level="medium"
    )


# ==================== КЛАВИАТУРЫ ====================

def get_main_keyboard(is_online=False):
    """Главная клавиатура врача"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Онлайн" if not is_online else "🔴 Оффлайн")],
            [KeyboardButton(text="📍 Отправить местоположение", request_location=True)],
            [KeyboardButton(text="📊 Мои статистики")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_call_keyboard(call_id):
    """Клавиатура для принятия/отказа от вызова"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{call_id}"),
                InlineKeyboardButton(text="❌ Отказаться", callback_data=f"decline_{call_id}")
            ]
        ]
    )
    return keyboard


def get_active_call_keyboard():
    """Клавиатура для активного вызова"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Я на месте")],
            [KeyboardButton(text="🚑 Вызвать бригаду"), KeyboardButton(text="✅ Завершить вызов")],
        ],
        resize_keyboard=True
    )
    return keyboard


# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    telegram_id = message.from_user.id
    
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if doctor:
        await message.answer(
            f"👨‍⚕️ Добро пожаловать, {doctor.first_name}!\n\n"
            f"Используйте кнопки для управления своим статусом.",
            reply_markup=get_main_keyboard(doctor.is_online)
        )
    else:
        await message.answer(
            "👋 Добро пожаловать в CivicHero!\n\n"
            "Для начала работы вам нужно зарегистрироваться.\n"
            "Используйте команду /register"
        )


@dp.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    """Начало регистрации врача"""
    telegram_id = message.from_user.id
    
    exists = await doctor_exists(telegram_id)
    if exists:
        await message.answer("Вы уже зарегистрированы!")
        return
    
    await message.answer("Давайте начнем регистрацию.\n\nКак вас зовут? (Имя)")
    await state.set_state(RegistrationStates.waiting_for_first_name)


@dp.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    """Обработка имени"""
    await state.update_data(first_name=message.text)
    await message.answer("Фамилия:")
    await state.set_state(RegistrationStates.waiting_for_last_name)


@dp.message(RegistrationStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Обработка фамилии"""
    await state.update_data(last_name=message.text)
    await message.answer("Номер телефона:")
    await state.set_state(RegistrationStates.waiting_for_phone)


@dp.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Завершение регистрации"""
    data = await state.get_data()
    
    doctor = await create_doctor(
        telegram_id=message.from_user.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=message.text
    )
    
    await state.clear()
    await message.answer(
        f"✅ Регистрация завершена!\n\n"
        f"👨‍⚕️ {doctor.first_name} {doctor.last_name}\n"
        f"📞 {doctor.phone}\n\n"
        f"Теперь вы можете изменить свой статус на 'Онлайн' для получения вызовов.",
        reply_markup=get_main_keyboard(False)
    )


# ==================== УПРАВЛЕНИЕ СТАТУСОМ ====================

@dp.message(F.text.in_(["🟢 Онлайн", "🔴 Оффлайн"]))
async def toggle_online_status(message: Message):
    """Переключение онлайн/оффлайн статуса"""
    telegram_id = message.from_user.id
    
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if not doctor:
        await message.answer("Сначала зарегистрируйтесь с помощью /register")
        return
    
    doctor = await toggle_doctor_status(telegram_id)
    
    status_text = "онлайн" if doctor.is_online else "оффлайн"
    await message.answer(
        f"✅ Ваш статус изменен на: {status_text}",
        reply_markup=get_main_keyboard(doctor.is_online)
    )


@dp.message(F.location)
async def update_location(message: Message):
    """Обновление местоположения врача"""
    telegram_id = message.from_user.id
    
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if not doctor:
        await message.answer("Сначала зарегистрируйтесь с помощью /register")
        return
    
    await update_doctor_location(
        telegram_id,
        message.location.latitude,
        message.location.longitude
    )
    
    await message.answer("✅ Ваше местоположение обновлено!")


# ==================== УВЕДОМЛЕНИЕ ВРАЧЕЙ ====================

async def notify_doctors_about_call(call_id):
    """Отправить уведомление всем онлайн врачам о новом вызове"""
    try:
        call = await get_call_by_id(call_id)
        if not call:
            print(f"Вызов {call_id} не найден")
            return
        
        online_doctors = await get_online_doctors_list()
        
        for doctor in online_doctors:
            distance = "неизвестно"
            if doctor.latitude and doctor.longitude and call.latitude and call.longitude:
                dist = calculate_distance(
                    doctor.latitude, doctor.longitude,
                    call.latitude, call.longitude
                )
                distance = f"{dist} км"
            
            message_text = (
                f"🚨 НОВЫЙ ВЫЗОВ #{call.id}\n\n"
                f"👤 Пациент: {call.patient_name}, {call.patient_age} лет\n"
                f"⚠️ Проблема: {call.illness_description}\n"
                f"📍 Адрес: {call.address}\n"
                f"🚦 Уровень угрозы: {call.get_threat_level_display()}\n"
                f"📏 Расстояние: {distance}\n\n"
                f"Примите или откажитесь от вызова:"
            )
            
            try:
                await bot.send_message(
                    doctor.telegram_id,
                    message_text,
                    reply_markup=get_call_keyboard(call.id)
                )
            except Exception as e:
                print(f"Ошибка отправки врачу {doctor.telegram_id}: {e}")
                
    except Exception as e:
        print(f"Ошибка при уведомлении врачей: {e}")


# ==================== ОБРАБОТКА ВЫЗОВОВ ====================

@dp.callback_query(F.data.startswith("accept_"))
async def accept_call_handler(callback: CallbackQuery, state: FSMContext):
    """Врач принимает вызов"""
    call_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    
    call, error = await accept_call_db(call_id, telegram_id)
    
    if error:
        await callback.answer(error, show_alert=True)
        return
    
    await callback.message.edit_text(
        f"✅ Вы приняли вызов #{call.id}\n\n"
        f"Адрес: {call.address}\n\n"
        f"⏱️ Таймер запущен. Когда прибудете на место, нажмите 'Я на месте'."
    )
    
    await callback.message.answer(
        "🚗 Вы в пути к пациенту.",
        reply_markup=get_active_call_keyboard()
    )
    
    # Сохраняем информацию о вызове в состоянии
    await state.update_data(active_call_id=call.id, arrival_time=datetime.now())
    await state.set_state(CallStates.on_call)
    
    await callback.answer()


@dp.callback_query(F.data.startswith("decline_"))
async def decline_call_handler(callback: CallbackQuery):
    """Врач отказывается от вызова"""
    await callback.message.edit_text("❌ Вы отказались от вызова")
    await callback.answer()


@dp.message(F.text == "📍 Я на месте", StateFilter(CallStates.on_call))
async def arrived_on_site(message: Message, state: FSMContext):
    """Врач прибыл на место"""
    data = await state.get_data()
    call_id = data.get('active_call_id')
    arrival_time = data.get('arrival_time')
    
    if not call_id:
        await message.answer("Ошибка: активный вызов не найден")
        return
    
    try:
        await update_call_on_site(call_id)
        
        time_to_arrival = (datetime.now() - arrival_time).seconds // 60 if arrival_time else 0
        
        await message.answer(
            f"✅ Вы на месте!\n"
            f"⏱️ Время в пути: {time_to_arrival} мин\n\n"
            f"Таймер вызова запущен."
        )
        
        # Обновляем состояние
        await state.update_data(on_site_time=datetime.now())
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@dp.message(F.text == "🚑 Вызвать бригаду", StateFilter(CallStates.on_call))
async def call_ambulance_handler(message: Message, state: FSMContext):
    """Вызов бригады скорой помощи"""
    data = await state.get_data()
    call_id = data.get('active_call_id')
    
    if not call_id:
        await message.answer("Ошибка: активный вызов не найден")
        return
    
    try:
        await call_ambulance_db(call_id)
        await message.answer("✅ Бригада скорой помощи вызвана!")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@dp.message(F.text == "✅ Завершить вызов", StateFilter(CallStates.on_call))
async def complete_call_request(message: Message, state: FSMContext):
    """Завершение вызова - запрос фото отчета"""
    await message.answer(
        "📸 Прикрепите фото отчет о выполненном вызове:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(CallStates.waiting_for_report_photo)


@dp.message(CallStates.waiting_for_report_photo, F.photo)
async def receive_report_photo(message: Message, state: FSMContext):
    """Получение фото отчета"""
    data = await state.get_data()
    call_id = data.get('active_call_id')
    on_site_time = data.get('on_site_time')
    
    if not call_id:
        await message.answer("Ошибка: активный вызов не найден")
        return
    
    try:
        call = await complete_call_db(call_id)
        
        duration = (datetime.now() - on_site_time).seconds // 60 if on_site_time else 0
        
        doctor = await get_doctor_by_telegram_id(message.from_user.id)
        
        await message.answer(
            f"✅ Вызов #{call.id} завершен!\n\n"
            f"⏱️ Длительность: {duration} мин\n"
            f"{'🚑 Бригада была вызвана' if call.ambulance_called else ''}\n\n"
            f"Спасибо за работу!",
            reply_markup=get_main_keyboard(doctor.is_online)
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@dp.message(CallStates.waiting_for_report_photo, F.text == "❌ Отмена")
async def cancel_completion(message: Message, state: FSMContext):
    """Отмена завершения вызова"""
    await message.answer(
        "Завершение отменено. Продолжайте работу с пациентом.",
        reply_markup=get_active_call_keyboard()
    )
    await state.set_state(CallStates.on_call)


# ==================== СТАТИСТИКА ====================

@dp.message(F.text == "📊 Мои статистики")
async def show_statistics(message: Message):
    """Показать статистику врача"""
    telegram_id = message.from_user.id
    
    try:
        doctor, completed_calls = await get_doctor_statistics(telegram_id)
        
        await message.answer(
            f"📊 Ваша статистика:\n\n"
            f"✅ Завершенных вызовов: {completed_calls}\n"
            f"🟢 Статус: {'Онлайн' if doctor.is_online else 'Оффлайн'}"
        )
    except Exception as e:
        await message.answer("Сначала зарегистрируйтесь с помощью /register")


# ==================== ТЕСТИРОВАНИЕ ====================

@dp.message(Command("test_call"))
async def test_call(message: Message):
    """Тестовая команда для создания вызова"""
    try:
        # Создаем тестовый вызов
        call = await create_test_call_db()
        
        # Уведомляем врачей
        await notify_doctors_about_call(call.id)
        await message.answer(f"✅ Создан тестовый вызов #{call.id}")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


# ==================== ЗАПУСК БОТА ====================

async def main():
    """Запуск бота"""
    print("🤖 Бот запущен!")
    print("📱 Ожидание сообщений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())