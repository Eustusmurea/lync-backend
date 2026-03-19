from rest_framework import serializers
from .models import InsuranceProvider, Invoice, InvoiceItem, Payment


class InsuranceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceProvider
        fields = '__all__'


class InvoiceItemSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='test_order.order_id', read_only=True)

    class Meta:
        model  = InvoiceItem
        fields = '__all__'
        read_only_fields = ['line_total']


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)

    class Meta:
        model  = Payment
        fields = '__all__'
        read_only_fields = ['paid_at', 'received_by']


class InvoiceSerializer(serializers.ModelSerializer):
    patient_name    = serializers.CharField(source='patient.full_name',       read_only=True)
    patient_mrn     = serializers.CharField(source='patient.mrn',             read_only=True)
    insurance_name  = serializers.CharField(source='insurance.name',          read_only=True, default='')
    created_by_name = serializers.CharField(source='created_by.get_full_name',read_only=True, default='')
    items           = InvoiceItemSerializer(many=True, read_only=True)
    payments        = PaymentSerializer(many=True,    read_only=True)

    class Meta:
        model  = Invoice
        fields = '__all__'
        read_only_fields = ['invoice_number', 'subtotal', 'discount_amt', 'tax_amt',
                            'total', 'amount_paid', 'balance', 'created_at', 'updated_at']


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model   = Invoice
        exclude = ['invoice_number', 'subtotal', 'discount_amt', 'tax_amt',
                   'total', 'amount_paid', 'balance']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice = Invoice.objects.create(**validated_data)
        for item in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item)
        return invoice
