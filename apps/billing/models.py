from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import decimal
from apps.samples.models import Patient
from apps.tests.models import TestOrder


class InsuranceProvider(models.Model):
    name          = models.CharField(max_length=200)
    code          = models.CharField(max_length=50, unique=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active     = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    STATUS = [
        ('draft',     'Draft'),
        ('issued',    'Issued'),
        ('partial',   'Partially Paid'),
        ('paid',      'Paid'),
        ('overdue',   'Overdue'),
        ('cancelled', 'Cancelled'),
        ('void',      'Void'),
    ]
    PAYMENT_METHODS = [
        ('cash',      'Cash'),
        ('mpesa',     'M-Pesa'),
        ('card',      'Credit / Debit Card'),
        ('insurance', 'Insurance'),
        ('bank',      'Bank Transfer'),
        ('waived',    'Waived'),
    ]

    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    patient        = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='invoices')
    visit          = models.ForeignKey(
        'visits.Visit', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoices',
    )
    insurance      = models.ForeignKey(InsuranceProvider, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='invoices')
    status         = models.CharField(max_length=20, choices=STATUS, default='draft')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True)
    subtotal       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_pct   = models.DecimalField(max_digits=5,  decimal_places=2, default=0)
    discount_amt   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_pct        = models.DecimalField(max_digits=5,  decimal_places=2, default=16)
    tax_amt        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total          = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes          = models.TextField(blank=True)
    issued_at      = models.DateTimeField(null=True, blank=True)
    due_date       = models.DateField(null=True, blank=True)
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='created_invoices')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = Invoice.objects.order_by('id').last()
            num = (last.id + 1) if last else 1
            self.invoice_number = f'INV-{num:05d}'
        TWO = decimal.Decimal('0.01')
        self.discount_amt = (self.subtotal * self.discount_pct / 100).quantize(TWO)
        taxable      = self.subtotal - self.discount_amt
        self.tax_amt = (taxable * self.tax_pct / 100).quantize(TWO)
        self.total   = taxable + self.tax_amt
        self.balance = self.total - self.amount_paid
        if self.status not in ('cancelled', 'void'):
            if self.balance <= 0 and self.total > 0:
                self.status = 'paid'
            elif self.amount_paid > 0 and self.balance > 0:
                self.status = 'partial'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.invoice_number} — {self.patient}'


class InvoiceItem(models.Model):
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    test_order  = models.ForeignKey(TestOrder, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='invoice_items')
    description = models.CharField(max_length=300)
    quantity    = models.PositiveIntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=10, decimal_places=2)
    line_total  = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        self.invoice.subtotal = sum(i.line_total for i in self.invoice.items.all())
        self.invoice.save()

    def __str__(self):
        return f'{self.invoice.invoice_number} — {self.description}'


class Payment(models.Model):
    METHOD = [
        ('cash',      'Cash'),
        ('mpesa',     'M-Pesa'),
        ('card',      'Credit / Debit Card'),
        ('insurance', 'Insurance'),
        ('bank',      'Bank Transfer'),
        ('waived',    'Waived'),
    ]

    invoice     = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount      = models.DecimalField(max_digits=12, decimal_places=2,
                                      validators=[MinValueValidator(decimal.Decimal('0.01'))])
    method      = models.CharField(max_length=20, choices=METHOD)
    reference   = models.CharField(max_length=100, blank=True)
    notes       = models.TextField(blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='received_payments')
    paid_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-paid_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        invoice = self.invoice
        invoice.amount_paid = sum(p.amount for p in invoice.payments.all())
        invoice.save()
        # Complete linked visit when fully paid
        visit = getattr(invoice, 'visit', None)
        if visit and invoice.status == 'paid' and visit.status != 'completed':
            from apps.visits.workflow import sync_visit_after_payment
            sync_visit_after_payment(visit)

    def __str__(self):
        return f'{self.invoice.invoice_number} — {self.method} {self.amount}'
