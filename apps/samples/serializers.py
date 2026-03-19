from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .models import Sample, Patient


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = '__all__'

    def get_age(self, obj):
        from datetime import date
        today = date.today()
        return today.year - obj.date_of_birth.year - (
            (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day)
        )


class SampleSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_mrn = serializers.CharField(source='patient.mrn', read_only=True)
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)

    class Meta:
        model = Sample
        fields = '__all__'
        read_only_fields = ['sample_id', 'received_at', 'barcode']


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    search_fields = ['first_name', 'last_name', 'mrn', 'phone']
    filterset_fields = ['gender']


class SampleViewSet(viewsets.ModelViewSet):
    queryset = Sample.objects.select_related('patient', 'received_by')
    serializer_class = SampleSerializer
    search_fields = ['sample_id', 'patient__first_name', 'patient__last_name', 'patient__mrn']
    filterset_fields = ['status', 'sample_type', 'priority']

    def perform_create(self, serializer):
        serializer.save(received_by=self.request.user)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        sample = self.get_object()
        sample.status = 'rejected'
        sample.rejection_reason = request.data.get('reason', '')
        sample.save()
        return Response(SampleSerializer(sample).data)


router = DefaultRouter()
router.register('patients', PatientViewSet, basename='patient')
router.register('', SampleViewSet, basename='sample')

urlpatterns = [path('', include(router.urls))]
