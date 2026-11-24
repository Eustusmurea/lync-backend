from rest_framework import serializers
from .models import TestPanel, TestParameter, TestOrder, TestResult, ResultAmendment


class TestParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestParameter
        fields = '__all__'


class TestPanelSerializer(serializers.ModelSerializer):
    parameters = TestParameterSerializer(many=True, read_only=True)

    class Meta:
        model = TestPanel
        fields = '__all__'


class ResultAmendmentSerializer(serializers.ModelSerializer):
    amended_by_name = serializers.CharField(source='amended_by.get_full_name', read_only=True)

    class Meta:
        model = ResultAmendment
        fields = '__all__'
        read_only_fields = ['amended_by', 'amended_at', 'previous_value', 'previous_numeric_value', 'previous_flag']


class TestResultSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)
    parameter_unit = serializers.CharField(source='parameter.unit', read_only=True)
    parameter_loinc = serializers.CharField(source='parameter.loinc_code', read_only=True)
    ref_range_low = serializers.FloatField(source='parameter.ref_range_low', read_only=True)
    ref_range_high = serializers.FloatField(source='parameter.ref_range_high', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    amendments = ResultAmendmentSerializer(many=True, read_only=True)

    class Meta:
        model = TestResult
        fields = '__all__'
        read_only_fields = ['entered_by', 'verified_by', 'entered_at', 'verified_at', 'flag']

    def validate(self, attrs):
        """Parameter must belong to the panel on the order."""
        order = attrs.get('order') or getattr(self.instance, 'order', None)
        parameter = attrs.get('parameter') or getattr(self.instance, 'parameter', None)

        if self.instance is None:
            if not order:
                raise serializers.ValidationError({'order': 'Order is required'})
            if not parameter:
                raise serializers.ValidationError({'parameter': 'Parameter is required'})

        if order and parameter and parameter.panel_id != order.panel_id:
            raise serializers.ValidationError(
                {'parameter': 'This parameter does not belong to the ordered test panel.'}
            )

        return attrs


class TestOrderSerializer(serializers.ModelSerializer):
    panel_name = serializers.CharField(source='panel.name', read_only=True)
    panel_code = serializers.CharField(source='panel.code', read_only=True)
    panel_loinc = serializers.CharField(source='panel.loinc_code', read_only=True)
    discipline = serializers.CharField(source='panel.discipline', read_only=True)
    sla_hours = serializers.FloatField(source='panel.sla_hours', read_only=True)
    patient = serializers.IntegerField(source='sample.patient_id', read_only=True)
    patient_name = serializers.CharField(source='sample.patient.full_name', read_only=True)
    patient_mrn = serializers.CharField(source='sample.patient.mrn', read_only=True)
    sample_code = serializers.CharField(source='sample.sample_id', read_only=True)
    sample_type = serializers.CharField(source='sample.sample_type', read_only=True)
    sample_barcode = serializers.UUIDField(source='sample.barcode', read_only=True)
    priority = serializers.CharField(source='sample.priority', read_only=True)
    ordered_by_name = serializers.CharField(source='ordered_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    parameters = TestParameterSerializer(source='panel.parameters', many=True, read_only=True)
    results = TestResultSerializer(many=True, read_only=True)
    turnaround_minutes = serializers.FloatField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = TestOrder
        fields = '__all__'
        read_only_fields = [
            'order_id', 'ordered_at', 'ordered_by', 'assigned_to', 'status',
            'started_at', 'completed_at', 'is_critical', 'critical_notified',
            'critical_notified_at',
        ]
