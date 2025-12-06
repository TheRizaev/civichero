from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Call, Doctor
from django.utils import timezone
import json
import requests
import os


BOT_HTTP_URL = 'http://localhost:8001'


def dashboard(request):
    """Main map dashboard with calls and doctors"""
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
    """Create a new emergency call"""
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
            'message': 'Call was successfully created'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def get_calls(request):
    """API – get all calls"""
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
    """Send call data to CivicHero bot (notify doctors)"""
    call = get_object_or_404(Call, id=call_id)
    
    if call.status not in ['created', 'sent_to_doctors']:
        return JsonResponse({
            'success': False,
            'error': 'Call is already being processed'
        }, status=400)
    
    # Update status
    call.status = 'sent_to_doctors'
    call.save()
    
    # Send request to bot
    try:
        response = requests.post(
            f"{BOT_HTTP_URL}/notify_call",
            json={'call_id': call_id},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            notified_count = result.get('notified_doctors', 0)
            return JsonResponse({
                'success': True,
                'message': f'Call successfully sent to CivicHero. Doctors notified: {notified_count}'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Call was created, but a problem occurred while notifying doctors',
                'warning': response.text
            })
            
    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'success': False,
            'error': 'Telegram bot is not running. Please check the worker service on Render.'
        }, status=503)
    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': True,
            'message': 'Call was created, but notification request took too long'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error while sending notification: {str(e)}'
        }, status=500)


def get_online_doctors(request):
    """API – online doctors"""
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
