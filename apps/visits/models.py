from django.db import models
from django.conf import settings
from apps.samples.models import Patient


class Visit(models.Model):
    STATUS_CHOICES = [
        ('registered',    'Registered'),
        ('triage',        'Triage / Vitals'),
        ('consultation',  'Doctor Consultation'),
        ('lab',           'Sent to Lab'),
        ('results_ready', 'Lab Results Ready'),
        ('prescription',  'Prescription Written'),
        ('pharmacy',      'At Pharmacy'),
        ('completed',     'Completed'),
        ('cancelled',     'Cancelled'),
    ]

    visit_number    = models.CharField(max_length=30, unique=True, editable=False)
    patient         = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='visits')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    chief_complaint = models.TextField(blank=True, help_text='Reason for visit')
    notes           = models.TextField(blank=True)

    # Timestamps per stage
    registered_at   = models.DateTimeField(auto_now_add=True)
    triage_at       = models.DateTimeField(null=True, blank=True)
    consultation_at = models.DateTimeField(null=True, blank=True)
    lab_at              = models.DateTimeField(null=True, blank=True)
    results_ready_at    = models.DateTimeField(null=True, blank=True)
    prescription_at     = models.DateTimeField(null=True, blank=True)
    pharmacy_at         = models.DateTimeField(null=True, blank=True)
    completed_at        = models.DateTimeField(null=True, blank=True)
    requires_lab        = models.BooleanField(default=True, help_text='Whether lab tests are expected for this visit')

    # Staff
    registered_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='registered_visits')
    attending_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='doctor_visits')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-registered_at']

    def save(self, *args, **kwargs):
        if not self.visit_number:
            last = Visit.objects.order_by('id').last()
            num  = (last.id + 1) if last else 1
            self.visit_number = f'VIS-{num:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.visit_number} — {self.patient}'

    def advance(self, to_status: str, user=None):
        """Move the visit forward in the workflow."""
        from django.utils import timezone
        ts_map = {
            'triage':         'triage_at',
            'consultation':   'consultation_at',
            'lab':            'lab_at',
            'results_ready':  'results_ready_at',
            'prescription':   'prescription_at',
            'pharmacy':       'pharmacy_at',
            'completed':      'completed_at',
        }
        self.status = to_status
        if to_status in ts_map:
            setattr(self, ts_map[to_status], timezone.now())
        if to_status == 'consultation' and user:
            self.attending_doctor = user
        self.save()


class Vitals(models.Model):
    visit           = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='vitals')
    blood_pressure  = models.CharField(max_length=20, blank=True, help_text='e.g. 120/80')
    pulse           = models.PositiveIntegerField(null=True, blank=True, help_text='bpm')
    temperature     = models.FloatField(null=True, blank=True, help_text='°C')
    weight          = models.FloatField(null=True, blank=True, help_text='kg')
    height          = models.FloatField(null=True, blank=True, help_text='cm')
    spo2            = models.FloatField(null=True, blank=True, help_text='% oxygen saturation')
    respiratory_rate= models.PositiveIntegerField(null=True, blank=True, help_text='breaths/min')
    bmi             = models.FloatField(null=True, blank=True)
    notes           = models.TextField(blank=True)
    recorded_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recorded_vitals')
    recorded_at     = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.weight and self.height and self.height > 0:
            h_m = self.height / 100
            self.bmi = round(self.weight / (h_m * h_m), 1)
        super().save(*args, **kwargs)
        # Advance visit to triage
        if self.visit.status == 'registered':
            self.visit.advance('triage', self.recorded_by)

    def __str__(self):
        return f'Vitals for {self.visit.visit_number}'


class Diagnosis(models.Model):
    visit             = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='diagnosis')
    doctor            = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='diagnoses')
    presenting_complaint = models.TextField(blank=True)
    examination_notes = models.TextField(blank=True)
    diagnosis         = models.TextField()
    icd_code          = models.CharField(max_length=20, blank=True, help_text='ICD-10 code')
    management_plan   = models.TextField(blank=True)
    follow_up         = models.TextField(blank=True)
    send_to_lab       = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.visit.status == 'results_ready':
            self.visit.advance('prescription', self.doctor)

    def __str__(self):
        return f'Diagnosis — {self.visit.visit_number}'


class VisitBillingEvent(models.Model):
    """Records a charge generated at each workflow stage."""
    STAGES = [
        ('registration',  'Registration'),
        ('consultation',  'Consultation'),
        ('lab',           'Laboratory'),
        ('pharmacy',      'Pharmacy'),
        ('other',         'Other'),
    ]

    visit       = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='billing_events')
    stage       = models.CharField(max_length=20, choices=STAGES)
    description = models.CharField(max_length=300)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.visit.visit_number} / {self.stage} — {self.amount}'
