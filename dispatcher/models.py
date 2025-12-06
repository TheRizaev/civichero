from django.db import models
from django.utils import timezone


class Doctor(models.Model):
    """Doctor profile"""
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
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"


class Call(models.Model):
    """Medical emergency call"""

    THREAT_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('created', 'Created'),
        ('sent_to_doctors', 'Sent to doctors'),
        ('accepted', 'Accepted by doctor'),
        ('on_way', 'Doctor on the way'),
        ('on_site', 'Doctor on site'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
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

    assigned_doctor = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='calls'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    on_site_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    report_photo = models.ImageField(upload_to='reports/', null=True, blank=True)
    report_text = models.TextField(blank=True)

    ambulance_called = models.BooleanField(default=False)
    ambulance_called_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Call #{self.id} - {self.patient_name}"

    class Meta:
        verbose_name = "Call"
        verbose_name_plural = "Calls"
        ordering = ['-created_at']


class CallResponse(models.Model):
    """Doctor's response to a call"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='responses')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='responses')
    responded_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    distance = models.FloatField(help_text="Distance in km")

    class Meta:
        verbose_name = "Call Response"
        verbose_name_plural = "Call Responses"
        unique_together = ['call', 'doctor']
