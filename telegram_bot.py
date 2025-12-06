import asyncio
import os
import sys
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from dispatcher.models import Doctor, Call
from django.utils import timezone as django_timezone
from asgiref.sync import sync_to_async

from bot_config import BOT_TOKEN, WEBHOOK_PORT

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


def calculate_distance(lat1, lon1, lat2, lon2):
    """Рассчитать расстояние между двумя точками по формуле Haversine (в км)"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return round(km, 2)


#работа с бд

@sync_to_async
def get_doctor_by_telegram_id(telegram_id):
    try:
        return Doctor.objects.get(telegram_id=telegram_id)
    except Doctor.DoesNotExist:
        return None


@sync_to_async
def doctor_exists(telegram_id):
    return Doctor.objects.filter(telegram_id=telegram_id).exists()


@sync_to_async
def create_doctor(telegram_id, first_name, last_name, phone):
    return Doctor.objects.create(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        phone=phone
    )


@sync_to_async
def toggle_doctor_status(telegram_id):
    doctor = Doctor.objects.get(telegram_id=telegram_id)
    doctor.is_online = not doctor.is_online
    doctor.save()
    return doctor


@sync_to_async
def update_doctor_location(telegram_id, latitude, longitude):
    doctor = Doctor.objects.get(telegram_id=telegram_id)
    doctor.latitude = latitude
    doctor.longitude = longitude
    doctor.save()
    return doctor


@sync_to_async
def get_call_by_id(call_id):
    try:
        return Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        return None


@sync_to_async
def get_online_doctors_list():
    return list(Doctor.objects.filter(is_online=True))


@sync_to_async
def accept_call_db(call_id, doctor_telegram_id):
    try:
        call = Call.objects.get(id=call_id)
        doctor = Doctor.objects.get(telegram_id=doctor_telegram_id)
        
        if call.status not in ['created', 'sent_to_doctors']:
            return None, "This call has already been accepted by another doctor."
        
        call.assigned_doctor = doctor
        call.status = 'accepted'
        call.accepted_at = django_timezone.now()
        call.save()
        return call, None
    except Exception as e:
        return None, str(e)


@sync_to_async
def update_call_on_site(call_id):
    call = Call.objects.get(id=call_id)
    call.status = 'on_site'
    call.on_site_at = django_timezone.now()
    call.save()
    return call


@sync_to_async
def call_ambulance_db(call_id):
    call = Call.objects.get(id=call_id)
    call.ambulance_called = True
    call.ambulance_called_at = django_timezone.now()
    call.save()
    return call


@sync_to_async
def complete_call_db(call_id):
    call = Call.objects.get(id=call_id)
    call.status = 'completed'
    call.completed_at = django_timezone.now()
    call.save()
    return call


@sync_to_async
def get_doctor_statistics(telegram_id):
    doctor = Doctor.objects.get(telegram_id=telegram_id)
    completed_calls_count = Call.objects.filter(
        assigned_doctor=doctor,
        status='completed'
    ).count()
    return doctor, completed_calls_count


@sync_to_async
def create_test_call_db():
    return Call.objects.create(
        patient_name="Test Patient",
        patient_age=45,
        patient_gender="male",
        illness_description="High blood pressure",
        address="Test street 123",
        latitude=41.2995,
        longitude=69.2401,
        threat_level="medium"
    )


def get_main_keyboard(is_online=False):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Go online" if not is_online else "🔴 Go offline")],
            [KeyboardButton(text="📍 Send location", request_location=True)],
            [KeyboardButton(text="📊 My statistics")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_call_keyboard(call_id):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_{call_id}"),
                InlineKeyboardButton(text="❌ Decline", callback_data=f"decline_{call_id}")
            ]
        ]
    )
    return keyboard


def get_active_call_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 I arrived")],
            [KeyboardButton(text="🚑 Call ambulance"), KeyboardButton(text="✅ Complete call")],
        ],
        resize_keyboard=True
    )
    return keyboard


# обработка команд

@dp.message(Command("start"))
async def cmd_start(message: Message):
    telegram_id = message.from_user.id
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if doctor:
        await message.answer(
            f"👨‍⚕️ Welcome, {doctor.first_name}!\n\n"
            f"Use the buttons to manage your status.",
            reply_markup=get_main_keyboard(doctor.is_online)
        )
    else:
        await message.answer(
            "👋 Welcome to CivicHero!\n\n"
            "To start using the bot, you need to register.\n"
            "Use the /register command."
        )


@dp.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    
    exists = await doctor_exists(telegram_id)
    if exists:
        await message.answer("You are already registered.")
        return
    
    await message.answer("Let's start your registration.\n\nWhat is your first name?")
    await state.set_state(RegistrationStates.waiting_for_first_name)


@dp.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Last name:")
    await state.set_state(RegistrationStates.waiting_for_last_name)


@dp.message(RegistrationStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Phone number:")
    await state.set_state(RegistrationStates.waiting_for_phone)


@dp.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    
    doctor = await create_doctor(
        telegram_id=message.from_user.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=message.text
    )
    
    await state.clear()
    await message.answer(
        f"✅ Registration completed!\n\n"
        f"👨‍⚕️ {doctor.first_name} {doctor.last_name}\n"
        f"📞 {doctor.phone}\n\n"
        f"Now you can go online to receive calls.",
        reply_markup=get_main_keyboard(False)
    )


# Управление статусом

@dp.message(F.text.in_(["🟢 Go online", "🔴 Go offline"]))
async def toggle_online_status(message: Message):
    telegram_id = message.from_user.id
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if not doctor:
        await message.answer("Please register using /register")
        return
    
    doctor = await toggle_doctor_status(telegram_id)
    status_text = "online" if doctor.is_online else "offline"
    await message.answer(
        f"✅ Your status is now: {status_text}",
        reply_markup=get_main_keyboard(doctor.is_online)
    )


@dp.message(F.location)
async def update_location(message: Message):
    telegram_id = message.from_user.id
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if not doctor:
        await message.answer("Please register using /register")
        return
    
    await update_doctor_location(
        telegram_id,
        message.location.latitude,
        message.location.longitude
    )
    await message.answer("✅ Your location was updated.")


# Уведомления врачей

async def notify_doctors_about_call(call_id):
    """Отправить уведомление всем онлайн врачам о новом вызове"""
    try:
        call = await get_call_by_id(call_id)
        if not call:
            print(f"Call {call_id} not found")
            return 0
        
        online_doctors = await get_online_doctors_list()
        notified_count = 0
        
        print(f"Found {len(online_doctors)} online doctors")
        
        for doctor in online_doctors:
            distance = "unknown"
            if doctor.latitude and doctor.longitude and call.latitude and call.longitude:
                dist = calculate_distance(
                    doctor.latitude, doctor.longitude,
                    call.latitude, call.longitude
                )
                distance = f"{dist} km"
            
            threat_display = dict(Call.THREAT_LEVELS).get(call.threat_level, call.threat_level)
            
            message_text = (
                f"🚨 NEW CALL #{call.id}\n\n"
                f"👤 Patient: {call.patient_name}, {call.patient_age} y/o\n"
                f"⚠️ Issue: {call.illness_description}\n"
                f"📍 Address: {call.address}\n"
                f"🚦 Threat level: {threat_display}\n"
                f"📏 Distance: {distance}\n\n"
                f"Choose Accept or Decline:"
            )
            
            try:
                await bot.send_message(
                    doctor.telegram_id,
                    message_text,
                    reply_markup=get_call_keyboard(call.id)
                )
                notified_count += 1
            except:
                pass
        
        return notified_count
                
    except:
        return 0


# http

async def handle_notify_call(request):
    try:
        data = await request.json()
        call_id = data.get('call_id')
        
        if not call_id:
            return web.json_response({'success': False, 'error': 'call_id is required'}, status=400)
        
        notified_count = await notify_doctors_about_call(call_id)
        
        return web.json_response({
            'success': True,
            'notified_doctors': notified_count,
            'message': f'Notified doctors: {notified_count}'
        })
        
    except Exception as e:
        return web.json_response({'success': False, 'error': str(e)}, status=500)


async def handle_health(request):
    return web.json_response({'status': 'ok', 'bot': 'running'})


# принятие вызова

@dp.callback_query(F.data.startswith("accept_"))
async def accept_call_handler(callback: CallbackQuery, state: FSMContext):
    call_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    
    call, error = await accept_call_db(call_id, telegram_id)
    
    if error:
        await callback.answer(error, show_alert=True)
        return
    
    await callback.message.edit_text(
        f"✅ You accepted call #{call.id}\n\n"
        f"Address: {call.address}\n\n"
        f"Drive to the patient location and press “I arrived”."
    )
    
    await callback.message.answer(
        "🚗 You are now on the way.",
        reply_markup=get_active_call_keyboard()
    )
    
    await state.update_data(active_call_id=call.id, arrival_time=datetime.now())
    await state.set_state(CallStates.on_call)
    await callback.answer()


@dp.callback_query(F.data.startswith("decline_"))
async def decline_call_handler(callback: CallbackQuery):
    await callback.message.edit_text("❌ You declined the call")
    await callback.answer()


# прибыл

@dp.message(F.text == "📍 I arrived", StateFilter(CallStates.on_call))
async def arrived_on_site(message: Message, state: FSMContext):
    data = await state.get_data()
    call_id = data.get('active_call_id')
    arrival_time = data.get('arrival_time')
    
    if not call_id:
        await message.answer("Error: active call not found.")
        return
    
    try:
        await update_call_on_site(call_id)
        time_to_arrival = (datetime.now() - arrival_time).seconds // 60 if arrival_time else 0
        
        await message.answer(
            f"✅ You arrived!\n"
            f"⏱️ Travel time: {time_to_arrival} minutes\n\n"
            f"Call timer started."
        )
        await state.update_data(on_site_time=datetime.now())
    except Exception as e:
        await message.answer(f"Error: {str(e)}")


# вызов скорой

@dp.message(F.text == "🚑 Call ambulance", StateFilter(CallStates.on_call))
async def call_ambulance_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    call_id = data.get('active_call_id')
    
    if not call_id:
        await message.answer("Error: active call not found")
        return
    
    try:
        await call_ambulance_db(call_id)
        await message.answer("✅ Ambulance has been called!")
    except Exception as e:
        await message.answer(f"Error: {str(e)}")


# Завершение вызова

@dp.message(F.text == "✅ Complete call", StateFilter(CallStates.on_call))
async def complete_call_request(message: Message, state: FSMContext):
    await message.answer(
        "📸 Please attach a photo report:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Cancel")]],
            resize_keyboard=True
        )
    )
    await state.set_state(CallStates.waiting_for_report_photo)


@dp.message(CallStates.waiting_for_report_photo, F.photo)
async def receive_report_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    call_id = data.get('active_call_id')
    on_site_time = data.get('on_site_time')
    
    if not call_id:
        await message.answer("Error: active call not found")
        return
    
    try:
        call = await complete_call_db(call_id)
        duration = (datetime.now() - on_site_time).seconds // 60 if on_site_time else 0
        doctor = await get_doctor_by_telegram_id(message.from_user.id)
        
        await message.answer(
            f"✅ Call #{call.id} completed!\n\n"
            f"⏱️ Duration: {duration} minutes\n"
            f"{'🚑 Ambulance was called' if call.ambulance_called else ''}\n\n"
            f"Thank you for your work!",
            reply_markup=get_main_keyboard(doctor.is_online)
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Error: {str(e)}")


@dp.message(CallStates.waiting_for_report_photo, F.text == "❌ Cancel")
async def cancel_completion(message: Message, state: FSMContext):
    await message.answer(
        "Completion cancelled. Continue working with the patient.",
        reply_markup=get_active_call_keyboard()
    )
    await state.set_state(CallStates.on_call)


# Стаистика

@dp.message(F.text == "📊 My statistics")
async def show_statistics(message: Message):
    telegram_id = message.from_user.id
    
    try:
        doctor, completed_calls = await get_doctor_statistics(telegram_id)
        await message.answer(
            f"📊 Your statistics:\n\n"
            f"✅ Completed calls: {completed_calls}\n"
            f"🟢 Status: {'Online' if doctor.is_online else 'Offline'}"
        )
    except:
        await message.answer("Please register using /register")


# тесты

@dp.message(Command("test_call"))
async def test_call(message: Message):
    try:
        call = await create_test_call_db()
        notified = await notify_doctors_about_call(call.id)
        await message.answer(f"✅ Test call #{call.id} created\nNotified doctors: {notified}")
    except Exception as e:
        await message.answer(f"Error: {str(e)}")


# Запуск бота

async def start_http_server():
    """Запуск HTTP сервера для приема запросов от Django"""
    app = web.Application()
    app.router.add_post('/notify_call', handle_notify_call)
    app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    print(f"HTTP server running on port {WEBHOOK_PORT}")
    return runner


async def main():
    """Запуск бота и HTTP сервера"""
    print("Bot starting...")
    runner = await start_http_server()
    print("Waiting for messages...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
