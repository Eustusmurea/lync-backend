from django.db import models
from django.conf import settings
import uuid


class Patient(models.Model):
    mrn = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.mrn} — {self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Sample(models.Model):
    TYPES = [
        ('blood', 'Blood'),
        ('urine', 'Urine'),
        ('swab', 'Swab'),
        ('tissue', 'Tissue'),
        ('csf', 'CSF'),
        ('stool', 'Stool'),
        ('sputum', 'Sputum'),
        ('other', 'Other'),
    ]
    PRIORITIES = [
        ('stat', 'STAT'),
        ('routine', 'Routine'),
        ('asap', 'ASAP'),
    ]
    STATUSES = [
        ('received', 'Received'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('rejected', 'Rejected'),
        ('hold', 'On Hold'),
    ]

    sample_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='samples')
    sample_type = models.CharField(max_length=20, choices=TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITIES, default='routine')
    status = models.CharField(max_length=20, choices=STATUSES, default='received')
    collection_site = models.CharField(max_length=200, blank=True)
    collected_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    collected_by = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='received_samples'
    )
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    barcode = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-received_at']

    def save(self, *args, **kwargs):
        if not self.sample_id:
            last = Sample.objects.order_by('id').last()
            num = (last.id + 1) if last else 1
            self.sample_id = f"SMP-{num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sample_id} ({self.patient})"
