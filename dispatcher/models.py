from django.db import models
from django.utils import timezone


class Doctor(models.Model):
    """Модель врача"""
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    username = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    is_online = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Врач"
        verbose_name_plural = "Врачи"


class Call(models.Model):
    """Модель вызова"""
    THREAT_LEVELS = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая'),
        ('critical', 'Критическая'),
    ]

    STATUS_CHOICES = [
        ('created', 'Создан'),
        ('sent_to_doctors', 'Отправлен врачам'),
        ('accepted', 'Принят врачом'),
        ('on_way', 'Врач в пути'),
        ('on_site', 'Врач на месте'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
    ]

    patient_name = models.CharField(max_length=200)
    patient_age = models.IntegerField()
    patient_gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    illness_description = models.TextField()
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    threat_level = models.CharField(max_length=10, choices=THREAT_LEVELS, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    assigned_doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    on_site_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    report_photo = models.ImageField(upload_to='reports/', null=True, blank=True)
    report_text = models.TextField(blank=True)
    ambulance_called = models.BooleanField(default=False)
    ambulance_called_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Вызов #{self.id} - {self.patient_name}"

    class Meta:
        verbose_name = "Вызов"
        verbose_name_plural = "Вызовы"
        ordering = ['-created_at']


class CallResponse(models.Model):
    """Модель ответа врача на вызов"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='responses')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='responses')
    responded_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    distance = models.FloatField(help_text="Расстояние в км")

    class Meta:
        verbose_name = "Ответ на вызов"
        verbose_name_plural = "Ответы на вызовы"
        unique_together = ['call', 'doctor']

