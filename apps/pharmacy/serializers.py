from rest_framework import serializers
from .models import (DrugCategory, Drug, DrugStockTransaction,
                     Prescription, PrescriptionItem, Dispense, DispenseItem,
                     OTCSale, OTCSaleItem)


class DrugCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = DrugCategory
        fields = '__all__'


class DrugSerializer(serializers.ModelSerializer):
    category_name    = serializers.CharField(source='category.name', read_only=True, default='')
    stock_level      = serializers.CharField(read_only=True)
    stock_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model  = Drug
        fields = '__all__'


class DrugStockTransactionSerializer(serializers.ModelSerializer):
    drug_name          = serializers.CharField(source='drug.name', read_only=True)
    performed_by_name  = serializers.CharField(source='performed_by.get_full_name', read_only=True)

    class Meta:
        model  = DrugStockTransaction
        fields = '__all__'
        read_only_fields = ['quantity_before', 'quantity_after', 'performed_by']


class PrescriptionItemSerializer(serializers.ModelSerializer):
    drug_name    = serializers.CharField(source='drug.name',     read_only=True)
    drug_form    = serializers.CharField(source='drug.form',     read_only=True)
    drug_strength= serializers.CharField(source='drug.strength', read_only=True)
    drug_unit    = serializers.CharField(source='drug.unit',     read_only=True)
    remaining    = serializers.FloatField(read_only=True)
    is_fully_dispensed = serializers.BooleanField(read_only=True)

    class Meta:
        model  = PrescriptionItem
        fields = '__all__'


class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name        = serializers.CharField(source='patient.full_name',         read_only=True)
    patient_mrn         = serializers.CharField(source='patient.mrn',               read_only=True)
    prescribed_by_name  = serializers.CharField(source='prescribed_by.get_full_name', read_only=True)
    items               = PrescriptionItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Prescription
        fields = '__all__'
        read_only_fields = ['rx_number', 'prescribed_at', 'created_at', 'updated_at']


class PrescriptionCreateSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, required=False)

    class Meta:
        model   = Prescription
        exclude = ['rx_number']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        rx = Prescription.objects.create(**validated_data)
        for item in items_data:
            PrescriptionItem.objects.create(prescription=rx, **item)
        return rx


class DispenseItemSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.name', read_only=True)

    class Meta:
        model  = DispenseItem
        fields = '__all__'


class DispenseSerializer(serializers.ModelSerializer):
    dispensed_by_name  = serializers.CharField(source='dispensed_by.get_full_name', read_only=True)
    patient_name       = serializers.CharField(source='prescription.patient.full_name', read_only=True)
    rx_number          = serializers.CharField(source='prescription.rx_number', read_only=True)
    items              = DispenseItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Dispense
        fields = '__all__'
        read_only_fields = ['dispense_id', 'dispensed_at']


class DispenseCreateSerializer(serializers.ModelSerializer):
    items = DispenseItemSerializer(many=True)

    class Meta:
        model   = Dispense
        exclude = ['dispense_id']

    def create(self, validated_data):
        from django.db import transaction

        items_data = validated_data.pop('items')
        prescription = validated_data.get('prescription')

        if not prescription:
            raise serializers.ValidationError({'prescription': 'Prescription is required for dispensing'})

        with transaction.atomic():
            dispense = Dispense.objects.create(**validated_data)
            for item in items_data:
                pres_item_id = item.get('prescription_item')
                qty = float(item.get('quantity_dispensed', 0))

                try:
                    pres_item = PrescriptionItem.objects.select_for_update().get(id=pres_item_id)
                except PrescriptionItem.DoesNotExist:
                    raise serializers.ValidationError({'items': f'Prescription item {pres_item_id} does not exist'})

                if pres_item.prescription_id != prescription.id:
                    raise serializers.ValidationError({'items': 'Prescription item does not belong to the specified prescription'})

                if qty <= 0:
                    raise serializers.ValidationError({'items': 'Quantity must be greater than zero'})

                if pres_item.remaining < qty:
                    raise serializers.ValidationError({'items': f'Requested quantity for item {pres_item_id} exceeds remaining quantity ({pres_item.remaining})'})

                # attach the prescription_item id to the item data expected by model
                item['prescription_item'] = pres_item.id
                # create the DispenseItem (this will deduct stock and update prescription)
                DispenseItem.objects.create(dispense=dispense, **item)

        return dispense


class OTCSaleItemSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model  = OTCSaleItem
        fields = ['id', 'drug', 'drug_name', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['id', 'line_total']

    def get_line_total(self, obj):
        return obj.line_total


class OTCSaleSerializer(serializers.ModelSerializer):
    patient_name     = serializers.CharField(source='patient.full_name', read_only=True, default='')
    patient_mrn      = serializers.CharField(source='patient.mrn', read_only=True, default='')
    dispensed_by_name= serializers.CharField(source='dispensed_by.get_full_name', read_only=True, default='')
    items            = OTCSaleItemSerializer(many=True, read_only=True)
    total_amount     = serializers.SerializerMethodField()

    class Meta:
        model  = OTCSale
        fields = '__all__'
        read_only_fields = ['sale_id', 'sold_at']

    def get_total_amount(self, obj):
        return obj.total_amount


class OTCSaleCreateSerializer(serializers.ModelSerializer):
    items = OTCSaleItemSerializer(many=True)

    class Meta:
        model   = OTCSale
        exclude = ['sale_id']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        sale = OTCSale.objects.create(**validated_data)
        for item in items_data:
            OTCSaleItem.objects.create(sale=sale, **item)
        return sale
