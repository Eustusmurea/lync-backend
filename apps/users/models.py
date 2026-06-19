from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [
        ('admin', 'Administrator'),
        ('receptionist', 'Receptionist'),
        ('clinician', 'Clinician'),
        ('technician', 'Lab Technician'),
        ('pharmacist', 'Pharmacist'),
        ('accountant', 'Accountant'),
        # Legacy roles (kept for existing records)
        ('manager', 'Lab Manager'),
        ('scientist', 'Lab Scientist'),
    ]

    role = models.CharField(max_length=20, choices=ROLES, default='receptionist')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
