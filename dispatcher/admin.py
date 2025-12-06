from django.contrib import admin
from .models import Doctor, Call, CallResponse


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone', 'is_online', 'created_at']
    list_filter = ['is_online', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'telegram_id']
    readonly_fields = ['created_at']


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient_name', 'patient_age', 'threat_level', 'status', 'assigned_doctor', 'created_at']
    list_filter = ['status', 'threat_level', 'patient_gender', 'created_at']
    search_fields = ['patient_name', 'address', 'illness_description']
    readonly_fields = ['created_at', 'accepted_at', 'on_site_at', 'completed_at', 'ambulance_called_at']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_name', 'patient_age', 'patient_gender', 'illness_description')
        }),
        ('Location', {
            'fields': ('address', 'latitude', 'longitude')
        }),
        ('Call Status', {
            'fields': ('threat_level', 'status', 'assigned_doctor')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'accepted_at', 'on_site_at', 'completed_at')
        }),
        ('Report', {
            'fields': ('report_photo', 'report_text', 'ambulance_called', 'ambulance_called_at')
        }),
    )


@admin.register(CallResponse)
class CallResponseAdmin(admin.ModelAdmin):
    list_display = ['call', 'doctor', 'accepted', 'distance', 'responded_at']
    list_filter = ['accepted', 'responded_at']
    search_fields = ['call__patient_name', 'doctor__first_name', 'doctor__last_name']
