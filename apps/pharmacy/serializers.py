from rest_framework import serializers
from .models import (DrugCategory, Drug, DrugStockTransaction,
                     Prescription, PrescriptionItem, Dispense, DispenseItem)


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
        items_data = validated_data.pop('items')
        dispense   = Dispense.objects.create(**validated_data)
        for item in items_data:
            DispenseItem.objects.create(dispense=dispense, **item)
        return dispense
