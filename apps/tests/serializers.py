from rest_framework import serializers
from .models import TestPanel, TestParameter, TestOrder, TestResult
from apps.samples.serializers import SampleSerializer


class TestParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestParameter
        fields = '__all__'


class TestPanelSerializer(serializers.ModelSerializer):
    parameters = TestParameterSerializer(many=True, read_only=True)

    class Meta:
        model = TestPanel
        fields = '__all__'


class TestResultSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)
    parameter_unit = serializers.CharField(source='parameter.unit', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)

    class Meta:
        model = TestResult
        fields = '__all__'


class TestOrderSerializer(serializers.ModelSerializer):
    panel_name = serializers.CharField(source='panel.name', read_only=True)
    patient_name = serializers.CharField(source='sample.patient.full_name', read_only=True)
    patient_mrn = serializers.CharField(source='sample.patient.mrn', read_only=True)
    ordered_by_name = serializers.CharField(source='ordered_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    results = TestResultSerializer(many=True, read_only=True)
    turnaround_minutes = serializers.FloatField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = TestOrder
        fields = '__all__'
        read_only_fields = ['order_id', 'ordered_at']
