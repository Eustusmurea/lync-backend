from rest_framework import serializers
from .models import Visit, Vitals, Diagnosis, VisitBillingEvent


class VitalsSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True, default='')

    class Meta:
        model  = Vitals
        fields = '__all__'
        read_only_fields = ['bmi', 'recorded_at', 'recorded_by']


class DiagnosisSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True, default='')

    class Meta:
        model  = Diagnosis
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'doctor']


class VisitBillingEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, default='')

    class Meta:
        model  = VisitBillingEvent
        fields = '__all__'
        read_only_fields = ['created_at', 'created_by']


class VisitSerializer(serializers.ModelSerializer):
    patient_name             = serializers.CharField(source='patient.full_name',           read_only=True)
    patient_mrn              = serializers.CharField(source='patient.mrn',                 read_only=True)
    patient_dob              = serializers.DateField(source='patient.date_of_birth',       read_only=True)
    patient_gender           = serializers.CharField(source='patient.gender',              read_only=True)
    patient_phone            = serializers.CharField(source='patient.phone',               read_only=True)
    registered_by_name       = serializers.CharField(source='registered_by.get_full_name', read_only=True, default='')
    attending_doctor_name    = serializers.CharField(source='attending_doctor.get_full_name', read_only=True, default='')
    vitals                   = VitalsSerializer(read_only=True)
    diagnosis                = DiagnosisSerializer(read_only=True)
    billing_events           = VisitBillingEventSerializer(many=True, read_only=True)
    # Related counts for the workflow UI
    test_orders_count        = serializers.SerializerMethodField()
    prescriptions_count      = serializers.SerializerMethodField()

    class Meta:
        model  = Visit
        fields = '__all__'
        read_only_fields = ['visit_number', 'registered_at', 'created_at', 'updated_at']

    def get_test_orders_count(self, obj):
        # Import here to avoid circular
        from apps.tests.models import TestOrder
        return TestOrder.objects.filter(sample__patient=obj.patient).count()

    def get_prescriptions_count(self, obj):
        from apps.pharmacy.models import Prescription
        return Prescription.objects.filter(patient=obj.patient).count()


class VisitReportSerializer(serializers.ModelSerializer):
    """Fat serializer for the print report — includes everything."""
    patient_name          = serializers.CharField(source='patient.full_name',       read_only=True)
    patient_mrn           = serializers.CharField(source='patient.mrn',             read_only=True)
    patient_dob           = serializers.DateField(source='patient.date_of_birth',   read_only=True)
    patient_gender        = serializers.CharField(source='patient.gender',          read_only=True)
    patient_phone         = serializers.CharField(source='patient.phone',           read_only=True)
    patient_email         = serializers.CharField(source='patient.email',           read_only=True)
    patient_address       = serializers.CharField(source='patient.address',         read_only=True)
    registered_by_name    = serializers.CharField(source='registered_by.get_full_name',     read_only=True, default='')
    attending_doctor_name = serializers.CharField(source='attending_doctor.get_full_name',  read_only=True, default='')
    vitals                = VitalsSerializer(read_only=True)
    diagnosis             = DiagnosisSerializer(read_only=True)
    billing_events        = VisitBillingEventSerializer(many=True, read_only=True)
    test_orders           = serializers.SerializerMethodField()
    prescriptions         = serializers.SerializerMethodField()

    class Meta:
        model  = Visit
        fields = '__all__'

    def get_test_orders(self, obj):
        from apps.tests.models import TestOrder
        from apps.tests.serializers import TestOrderSerializer
        orders = TestOrder.objects.filter(
            sample__patient=obj.patient,
            ordered_at__date=obj.registered_at.date()
        ).prefetch_related('results__parameter')
        return TestOrderSerializer(orders, many=True).data

    def get_prescriptions(self, obj):
        from apps.pharmacy.models import Prescription
        from apps.pharmacy.serializers import PrescriptionSerializer
        rxs = Prescription.objects.filter(
            patient=obj.patient,
            prescribed_at__date=obj.registered_at.date()
        ).prefetch_related('items__drug')
        return PrescriptionSerializer(rxs, many=True).data
