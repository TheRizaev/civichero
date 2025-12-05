from django.urls import path
from . import views

app_name = 'dispatcher'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/calls/', views.get_calls, name='get_calls'),
    path('api/calls/create/', views.create_call, name='create_call'),
    path('api/calls/<int:call_id>/assign/', views.assign_to_civichero, name='assign_to_civichero'),
    path('api/doctors/online/', views.get_online_doctors, name='get_online_doctors'),
]
