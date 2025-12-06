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


# States for registraion
class RegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_phone = State()


# States for call
class CallStates(StatesGroup):
    waiting_for_report_photo = State()
    on_call = State()


def calculate_distance(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return round(km, 2)


#Work with DB

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
            return None, "Ushbu chaqiruv allaqachon boshqa shifokor tomonidan qabul qilingan."
        
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
        patient_name="Test Bemor",
        patient_age=45,
        patient_gender="male",
        illness_description="Qon bosimi yuqori",
        address="Test ko'chasi 123",
        latitude=41.2995,
        longitude=69.2401,
        threat_level="medium"
    )


def get_main_keyboard(is_online=False):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Onlayn rejim" if not is_online else "🔴 Oflayn rejim")],
            [KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)],
            [KeyboardButton(text="📊 Mening statistikalarim")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_call_keyboard(call_id):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_{call_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"decline_{call_id}")
            ]
        ]
    )
    return keyboard


def get_active_call_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Yetib keldim")],
            [KeyboardButton(text="🚑 Tez yordam chaqirish"), KeyboardButton(text="✅ Chaqiruvni yakunlash")],
        ],
        resize_keyboard=True
    )
    return keyboard


# Comand processing

@dp.message(Command("start"))
async def cmd_start(message: Message):
    telegram_id = message.from_user.id
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if doctor:
        await message.answer(
            f"👨‍⚕️ Xush kelibsiz, {doctor.first_name}!\n\n"
            f"Statusingizni boshqarish uchun tugmalardan foydalaning.",
            reply_markup=get_main_keyboard(doctor.is_online)
        )
    else:
        await message.answer(
            "👋 CivicHero-ga xush kelibsiz!\n\n"
            "Botdan foydalanishni boshlash uchun ro'yxatdan o'tishingiz kerak.\n"
            "/register buyrug'idan foydalaning."
        )


@dp.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    
    exists = await doctor_exists(telegram_id)
    if exists:
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz.")
        return
    
    await message.answer("Ro'yxatdan o'tishni boshlaymiz.\n\nIsmingiz nima?")
    await state.set_state(RegistrationStates.waiting_for_first_name)


@dp.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Familiyangiz:")
    await state.set_state(RegistrationStates.waiting_for_last_name)


@dp.message(RegistrationStates.waiting_for_last_name)
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Telefon raqamingiz:")
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
        f"✅ Ro'yxatdan o'tish yakunlandi!\n\n"
        f"👨‍⚕️ {doctor.first_name} {doctor.last_name}\n"
        f"📞 {doctor.phone}\n\n"
        f"Endi chaqiruvlarni qabul qilish uchun 'Onlayn rejim'ga o'tishingiz mumkin.",
        reply_markup=get_main_keyboard(False)
    )


# Status management

@dp.message(F.text.in_(["🟢 Onlayn rejim", "🔴 Oflayn rejim"]))
async def toggle_online_status(message: Message):
    telegram_id = message.from_user.id
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if not doctor:
        await message.answer("Iltimos, avval /register orqali ro'yxatdan o'ting")
        return
    
    doctor = await toggle_doctor_status(telegram_id)
    status_text = "onlayn" if doctor.is_online else "oflayn"
    await message.answer(
        f"✅ Sizning statusingiz: {status_text}",
        reply_markup=get_main_keyboard(doctor.is_online)
    )


@dp.message(F.location)
async def update_location(message: Message):
    telegram_id = message.from_user.id
    doctor = await get_doctor_by_telegram_id(telegram_id)
    
    if not doctor:
        await message.answer("Iltimos, avval /register orqali ro'yxatdan o'ting")
        return
    
    await update_doctor_location(
        telegram_id,
        message.location.latitude,
        message.location.longitude
    )
    await message.answer("✅ Sizning joylashuvingiz yangilandi.")


# Notify doctors

async def notify_doctors_about_call(call_id):
    try:
        call = await get_call_by_id(call_id)
        if not call:
            print(f"Call {call_id} not found")
            return 0
        
        online_doctors = await get_online_doctors_list()
        notified_count = 0
        
        print(f"Found {len(online_doctors)} online doctors")
        
        for doctor in online_doctors:
            distance = "noma'lum"
            if doctor.latitude and doctor.longitude and call.latitude and call.longitude:
                dist = calculate_distance(
                    doctor.latitude, doctor.longitude,
                    call.latitude, call.longitude
                )
                distance = f"{dist} km"
            
            threat_display = dict(Call.THREAT_LEVELS).get(call.threat_level, call.threat_level)
            
            message_text = (
                f"🚨 YANGI CHAQIRUV #{call.id}\n\n"
                f"👤 Bemor: {call.patient_name}, {call.patient_age} yosh\n"
                f"⚠️ Shikoyat: {call.illness_description}\n"
                f"📍 Manzil: {call.address}\n"
                f"🚦 Xavf darajasi: {threat_display}\n"
                f"📏 Masofa: {distance}\n\n"
                f"Qabul qilish yoki Rad etishni tanlang:"
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


# Accepting calls

@dp.callback_query(F.data.startswith("accept_"))
async def accept_call_handler(callback: CallbackQuery, state: FSMContext):
    call_id = int(callback.data.split("_")[1])
    telegram_id = callback.from_user.id
    
    call, error = await accept_call_db(call_id, telegram_id)
    
    if error:
        await callback.answer(error, show_alert=True)
        return
    
    await callback.message.edit_text(
        f"✅ Siz #{call.id} chaqiruvni qabul qildingiz\n\n"
        f"Manzil: {call.address}\n\n"
        f"Bemor manziliga boring va “Yetib keldim” tugmasini bosing."
    )
    
    await callback.message.answer(
        "🚗 Siz yo'lga chiqdingiz.",
        reply_markup=get_active_call_keyboard()
    )
    
    await state.update_data(active_call_id=call.id, arrival_time=datetime.now())
    await state.set_state(CallStates.on_call)
    await callback.answer()


@dp.callback_query(F.data.startswith("decline_"))
async def decline_call_handler(callback: CallbackQuery):
    await callback.message.edit_text("❌ Siz chaqiruvni rad etdingiz")
    await callback.answer()


# Arrived

@dp.message(F.text == "📍 Yetib keldim", StateFilter(CallStates.on_call))
async def arrived_on_site(message: Message, state: FSMContext):
    data = await state.get_data()
    call_id = data.get('active_call_id')
    arrival_time = data.get('arrival_time')
    
    if not call_id:
        await message.answer("Xatolik: faol chaqiruv topilmadi.")
        return
    
    try:
        await update_call_on_site(call_id)
        time_to_arrival = (datetime.now() - arrival_time).seconds // 60 if arrival_time else 0
        
        await message.answer(
            f"✅ Siz yetib keldingiz!\n"
            f"⏱️ Yo'l vaqti: {time_to_arrival} daqiqa\n\n"
            f"Chaqiruv taymeri ishga tushdi."
        )
        await state.update_data(on_site_time=datetime.now())
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")


# Call an ambulance

@dp.message(F.text == "🚑 Tez yordam chaqirish", StateFilter(CallStates.on_call))
async def call_ambulance_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    call_id = data.get('active_call_id')
    
    if not call_id:
        await message.answer("Xatolik: faol chaqiruv topilmadi")
        return
    
    try:
        await call_ambulance_db(call_id)
        await message.answer("✅ Tez yordam chaqirildi!")
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")


# Finishing call

@dp.message(F.text == "✅ Chaqiruvni yakunlash", StateFilter(CallStates.on_call))
async def complete_call_request(message: Message, state: FSMContext):
    await message.answer(
        "📸 Iltimos, hisobot rasmini yuklang:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
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
        await message.answer("Xatolik: faol chaqiruv topilmadi")
        return
    
    try:
        call = await complete_call_db(call_id)
        duration = (datetime.now() - on_site_time).seconds // 60 if on_site_time else 0
        doctor = await get_doctor_by_telegram_id(message.from_user.id)
        
        await message.answer(
            f"✅ Chaqiruv #{call.id} yakunlandi!\n\n"
            f"⏱️ Davomiyligi: {duration} daqiqa\n"
            f"{'🚑 Tez yordam chaqirilgan' if call.ambulance_called else ''}\n\n"
            f"Xizmatlaringiz uchun rahmat!",
            reply_markup=get_main_keyboard(doctor.is_online)
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")


@dp.message(CallStates.waiting_for_report_photo, F.text == "❌ Bekor qilish")
async def cancel_completion(message: Message, state: FSMContext):
    await message.answer(
        "Yakunlash bekor qilindi. Bemor bilan ishlashda davom eting.",
        reply_markup=get_active_call_keyboard()
    )
    await state.set_state(CallStates.on_call)


# Stats

@dp.message(F.text == "📊 Mening statistikalarim")
async def show_statistics(message: Message):
    telegram_id = message.from_user.id
    
    try:
        doctor, completed_calls = await get_doctor_statistics(telegram_id)
        await message.answer(
            f"📊 Sizning statistikalaringiz:\n\n"
            f"✅ Yakunlangan chaqiruvlar: {completed_calls}\n"
            f"🟢 Status: {'Onlayn' if doctor.is_online else 'Oflayn'}"
        )
    except:
        await message.answer("Iltimos, avval /register orqali ro'yxatdan o'ting")


# Tests

@dp.message(Command("test_call"))
async def test_call(message: Message):
    try:
        call = await create_test_call_db()
        notified = await notify_doctors_about_call(call.id)
        await message.answer(f"✅ Test chaqiruvi #{call.id} yaratildi\nXabardor qilingan shifokorlar: {notified}")
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")


# Launching bot

async def start_http_server():
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
    print("Bot starting...")
    runner = await start_http_server()
    print("Waiting for messages...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
