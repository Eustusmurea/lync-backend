from django.db import models
from django.conf import settings


class ReagentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Reagent(models.Model):
    UNITS = [
        ('ml', 'mL'),
        ('l', 'L'),
        ('mg', 'mg'),
        ('g', 'g'),
        ('units', 'Units'),
        ('tests', 'Tests'),
        ('vials', 'Vials'),
        ('kits', 'Kits'),
    ]

    name = models.CharField(max_length=200)
    catalog_number = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(ReagentCategory, on_delete=models.SET_NULL, null=True, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    supplier = models.CharField(max_length=200, blank=True)
    unit = models.CharField(max_length=20, choices=UNITS, default='units')
    stock_quantity = models.FloatField(default=0)
    reorder_level = models.FloatField(default=10)
    max_stock = models.FloatField(default=100)
    storage_condition = models.CharField(max_length=100, blank=True, help_text='e.g. 2–8°C, Room temp')
    expiry_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True, help_text='Fridge/shelf location')
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.catalog_number})"

    @property
    def stock_level(self):
        if self.stock_quantity <= self.reorder_level:
            return 'low'
        elif self.stock_quantity <= self.reorder_level * 1.5:
            return 'warning'
        return 'ok'

    @property
    def stock_percentage(self):
        if self.max_stock == 0:
            return 0
        return min(round((self.stock_quantity / self.max_stock) * 100, 1), 100)


class StockTransaction(models.Model):
    TYPES = [
        ('receive', 'Received'),
        ('consume', 'Consumed'),
        ('adjust', 'Adjustment'),
        ('dispose', 'Disposed'),
    ]

    reagent = models.ForeignKey(Reagent, on_delete=models.PROTECT, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    quantity = models.FloatField()
    quantity_before = models.FloatField()
    quantity_after = models.FloatField()
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reagent.name} — {self.transaction_type} {self.quantity}"
