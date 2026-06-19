from django.db import models
from django.conf import settings
from apps.samples.models import Sample


class TestPanel(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    sla_hours = models.FloatField(default=4.0, help_text='Turnaround time target in hours')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.name}"


class TestParameter(models.Model):
    panel = models.ForeignKey(TestPanel, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=30, blank=True)
    ref_range_low = models.FloatField(null=True, blank=True)
    ref_range_high = models.FloatField(null=True, blank=True)
    critical_low = models.FloatField(null=True, blank=True)
    critical_high = models.FloatField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.panel.code} — {self.name}"


class TestOrder(models.Model):
    STATUSES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('review', 'Awaiting Review'),
        ('cancelled', 'Cancelled'),
    ]

    order_id = models.CharField(max_length=20, unique=True, editable=False)
    sample = models.ForeignKey(Sample, on_delete=models.PROTECT, related_name='test_orders')
    visit = models.ForeignKey(
        'visits.Visit', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='test_orders',
    )
    panel = models.ForeignKey(TestPanel, on_delete=models.PROTECT)
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ordered_tests'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tests'
    )
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    ordered_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_critical = models.BooleanField(default=False)
    critical_notified = models.BooleanField(default=False)
    critical_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-ordered_at']

    def save(self, *args, **kwargs):
        if not self.order_id:
            last = TestOrder.objects.order_by('id').last()
            num = (last.id + 1) if last else 1
            self.order_id = f"ORD-{num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} — {self.panel.name}"

    @property
    def turnaround_minutes(self):
        if self.completed_at and self.ordered_at:
            delta = self.completed_at - self.ordered_at
            return round(delta.total_seconds() / 60, 1)
        return None

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.status == 'complete':
            return False
        elapsed_hours = (timezone.now() - self.ordered_at).total_seconds() / 3600
        return elapsed_hours > self.panel.sla_hours


class TestResult(models.Model):
    FLAGS = [
        ('normal', 'Normal'),
        ('high', 'High'),
        ('low', 'Low'),
        ('critical_high', 'Critical High'),
        ('critical_low', 'Critical Low'),
    ]

    order = models.ForeignKey(TestOrder, on_delete=models.CASCADE, related_name='results')
    parameter = models.ForeignKey(TestParameter, on_delete=models.PROTECT)
    value = models.CharField(max_length=100)
    numeric_value = models.FloatField(null=True, blank=True)
    flag = models.CharField(max_length=20, choices=FLAGS, default='normal')
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='entered_results'
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_results'
    )
    entered_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ['order', 'parameter']
        ordering = ['parameter__order']

    def __str__(self):
        return f"{self.order.order_id} — {self.parameter.name}: {self.value}"
