from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import decimal
from apps.samples.models import Patient


class DrugCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Drug(models.Model):
    FORMS = [
        ('tablet',   'Tablet'),
        ('capsule',  'Capsule'),
        ('syrup',    'Syrup / Liquid'),
        ('injection','Injection'),
        ('cream',    'Cream / Ointment'),
        ('drops',    'Drops'),
        ('inhaler',  'Inhaler'),
        ('patch',    'Patch'),
        ('suppository','Suppository'),
        ('other',    'Other'),
    ]
    UNITS = [
        ('tablet', 'Tablet(s)'),
        ('capsule','Capsule(s)'),
        ('ml',     'mL'),
        ('mg',     'mg'),
        ('g',      'g'),
        ('vial',   'Vial(s)'),
        ('ampoule','Ampoule(s)'),
        ('tube',   'Tube(s)'),
        ('bottle', 'Bottle(s)'),
        ('sachet', 'Sachet(s)'),
        ('unit',   'Unit(s)'),
    ]

    name             = models.CharField(max_length=200)
    generic_name     = models.CharField(max_length=200, blank=True)
    brand_name       = models.CharField(max_length=200, blank=True)
    category         = models.ForeignKey(DrugCategory, on_delete=models.SET_NULL, null=True, blank=True)
    form             = models.CharField(max_length=20, choices=FORMS, default='tablet')
    strength         = models.CharField(max_length=50, blank=True, help_text='e.g. 500mg, 250mg/5mL')
    unit             = models.CharField(max_length=20, choices=UNITS, default='tablet')
    stock_quantity   = models.FloatField(default=0, validators=[MinValueValidator(0)])
    reorder_level    = models.FloatField(default=50, help_text='Alert when stock falls below this')
    max_stock        = models.FloatField(default=500)
    unit_price       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    storage_condition= models.CharField(max_length=100, blank=True, help_text='e.g. Below 25°C, Refrigerate')
    location         = models.CharField(max_length=100, blank=True, help_text='Shelf / bin location')
    supplier         = models.CharField(max_length=200, blank=True)
    expiry_date      = models.DateField(null=True, blank=True)
    barcode          = models.CharField(max_length=100, blank=True)
    controlled       = models.BooleanField(default=False, help_text='Controlled / narcotic substance')
    is_active        = models.BooleanField(default=True)
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        return ' '.join(parts)

    @property
    def stock_level(self):
        if self.stock_quantity <= 0:
            return 'out'
        if self.stock_quantity <= self.reorder_level:
            return 'low'
        if self.stock_quantity <= self.reorder_level * 1.5:
            return 'warning'
        return 'ok'

    @property
    def stock_percentage(self):
        if self.max_stock == 0:
            return 0
        return min(round((self.stock_quantity / self.max_stock) * 100, 1), 100)


class DrugStockTransaction(models.Model):
    TYPES = [
        ('receive',  'Stock Received'),
        ('dispense', 'Dispensed'),
        ('adjust',   'Adjustment'),
        ('return',   'Returned'),
        ('expire',   'Expired / Disposed'),
    ]

    drug             = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    quantity         = models.FloatField()
    quantity_before  = models.FloatField()
    quantity_after   = models.FloatField()
    reference        = models.CharField(max_length=100, blank=True, help_text='Dispense ID, batch, etc.')
    performed_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                         null=True, blank=True)
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.drug} — {self.transaction_type} {self.quantity}'


class Prescription(models.Model):
    STATUS = [
        ('active',     'Active'),
        ('partial',    'Partially Dispensed'),
        ('dispensed',  'Fully Dispensed'),
        ('cancelled',  'Cancelled'),
        ('expired',    'Expired'),
    ]

    rx_number    = models.CharField(max_length=30, unique=True, editable=False)
    patient      = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='prescriptions')
    prescribed_by= models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='prescriptions_written')
    status       = models.CharField(max_length=20, choices=STATUS, default='active')
    diagnosis    = models.TextField(blank=True)
    notes        = models.TextField(blank=True)
    prescribed_at= models.DateTimeField(auto_now_add=True)
    valid_until  = models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-prescribed_at']

    def save(self, *args, **kwargs):
        if not self.rx_number:
            last = Prescription.objects.order_by('id').last()
            num = (last.id + 1) if last else 1
            self.rx_number = f'RX-{num:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.rx_number} — {self.patient}'


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    drug         = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name='prescription_items')
    dose         = models.CharField(max_length=100, help_text='e.g. 500mg, 2 tablets')
    frequency    = models.CharField(max_length=100, help_text='e.g. Twice daily, Every 8 hours')
    duration     = models.CharField(max_length=100, help_text='e.g. 7 days, 2 weeks')
    quantity     = models.FloatField(help_text='Total quantity to dispense')
    dispensed_qty= models.FloatField(default=0)
    instructions = models.TextField(blank=True, help_text='e.g. Take after meals')

    class Meta:
        ordering = ['id']

    @property
    def remaining(self):
        return max(self.quantity - self.dispensed_qty, 0)

    @property
    def is_fully_dispensed(self):
        return self.dispensed_qty >= self.quantity

    def __str__(self):
        return f'{self.prescription.rx_number} — {self.drug}'


class Dispense(models.Model):
    dispense_id   = models.CharField(max_length=30, unique=True, editable=False)
    prescription  = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name='dispenses')
    dispensed_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='dispenses')
    notes         = models.TextField(blank=True)
    dispensed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-dispensed_at']

    def save(self, *args, **kwargs):
        if not self.dispense_id:
            last = Dispense.objects.order_by('id').last()
            num = (last.id + 1) if last else 1
            self.dispense_id = f'DIS-{num:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.dispense_id} — {self.prescription.rx_number}'


class DispenseItem(models.Model):
    dispense          = models.ForeignKey(Dispense, on_delete=models.CASCADE, related_name='items')
    prescription_item = models.ForeignKey(PrescriptionItem, on_delete=models.PROTECT,
                                          related_name='dispense_items')
    drug              = models.ForeignKey(Drug, on_delete=models.PROTECT)
    quantity_dispensed= models.FloatField(validators=[MinValueValidator(0.01)])
    batch_number      = models.CharField(max_length=100, blank=True)
    expiry_date       = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Deduct from drug stock
        drug = self.drug
        before = drug.stock_quantity
        drug.stock_quantity = max(0, drug.stock_quantity - self.quantity_dispensed)
        drug.save()
        DrugStockTransaction.objects.update_or_create(
            drug=drug,
            reference=self.dispense.dispense_id,
            transaction_type='dispense',
            defaults={
                'quantity':       self.quantity_dispensed,
                'quantity_before': before,
                'quantity_after':  drug.stock_quantity,
                'performed_by':   self.dispense.dispensed_by,
            }
        )
        # Update dispensed qty on prescription item
        item = self.prescription_item
        item.dispensed_qty += self.quantity_dispensed
        item.save()
        # Update prescription status
        rx = item.prescription
        all_items = rx.items.all()
        if all(i.is_fully_dispensed for i in all_items):
            rx.status = 'dispensed'
        elif any(i.dispensed_qty > 0 for i in all_items):
            rx.status = 'partial'
        rx.save()

    def __str__(self):
        return f'{self.dispense.dispense_id} — {self.drug} x{self.quantity_dispensed}'
