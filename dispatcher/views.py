from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Call, Doctor
from django.utils import timezone
import json


def dashboard(request):
    """Главная страница с картой и списком вызовов"""
    calls = Call.objects.all()
    online_doctors = Doctor.objects.filter(is_online=True)
    
    context = {
        'calls': calls,
        'online_doctors': online_doctors,
        'tashkent_center': {'lat': 41.2995, 'lng': 69.2401}
    }
    return render(request, 'dispatcher/dashboard.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def create_call(request):
    """Создание нового вызова"""
    try:
        data = json.loads(request.body)
        
        call = Call.objects.create(
            patient_name=data.get('patient_name'),
            patient_age=data.get('patient_age'),
            patient_gender=data.get('patient_gender'),
            illness_description=data.get('condition'),
            address=data.get('address'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            threat_level=data.get('threat_level'),
        )
        
        return JsonResponse({
            'success': True,
            'call_id': call.id,
            'message': 'Вызов успешно создан'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def get_calls(request):
    """API для получения списка всех вызовов"""
    calls = Call.objects.all().select_related('assigned_doctor')
    
    calls_data = []
    for call in calls:
        calls_data.append({
            'id': call.id,
            'patient_name': call.patient_name,
            'patient_age': call.patient_age,
            'patient_gender': call.patient_gender,
            'condition': call.illness_description,
            'address': call.address,
            'latitude': call.latitude,
            'longitude': call.longitude,
            'threat_level': call.threat_level,
            'status': call.status,
            'assigned_doctor': call.assigned_doctor.first_name + ' ' + call.assigned_doctor.last_name if call.assigned_doctor else None,
            'created_at': call.created_at.isoformat(),
        })
    
    return JsonResponse({'calls': calls_data})


@csrf_exempt
@require_http_methods(["POST"])
def assign_to_civichero(request, call_id):
    """Передать вызов в систему CivicHero (отправка врачам)"""
    call = get_object_or_404(Call, id=call_id)
    
    if call.status not in ['created', 'sent_to_doctors']:
        return JsonResponse({
            'success': False,
            'error': 'Вызов уже обрабатывается'
        }, status=400)
    
    # Обновляем статус вызова
    call.status = 'sent_to_doctors'
    call.save()
    
    # Здесь будет отправка уведомления врачам через Telegram
    # Это будет обрабатываться ботом
    
    return JsonResponse({
        'success': True,
        'message': 'Вызов передан врачам CivicHero'
    })


def get_online_doctors(request):
    """API для получения онлайн врачей"""
    doctors = Doctor.objects.filter(is_online=True)
    
    doctors_data = []
    for doctor in doctors:
        doctors_data.append({
            'id': doctor.id,
            'telegram_id': doctor.telegram_id,
            'name': f"{doctor.first_name} {doctor.last_name}",
            'latitude': doctor.latitude,
            'longitude': doctor.longitude,
        })
    
    return JsonResponse({'doctors': doctors_data})

