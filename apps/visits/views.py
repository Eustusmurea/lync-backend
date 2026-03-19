from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import Visit, Vitals, Diagnosis, VisitBillingEvent
from .serializers import (
    VisitSerializer, VisitReportSerializer,
    VitalsSerializer, DiagnosisSerializer,
    VisitBillingEventSerializer,
)


class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.select_related(
        'patient', 'registered_by', 'attending_doctor'
    ).prefetch_related('billing_events')
    serializer_class = VisitSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['status', 'patient']
    search_fields    = ['visit_number', 'patient__first_name',
                        'patient__last_name', 'patient__mrn']

    def perform_create(self, serializer):
        serializer.save(registered_by=self.request.user)

    # ── Workflow transitions ──────────────────────────────────────────────────
    @action(detail=True, methods=['post'])
    def advance(self, request, pk=None):
        visit = self.get_object()
        to    = request.data.get('status')
        valid = [s for s, _ in Visit.STATUS_CHOICES]
        if to not in valid:
            return Response({'error': f'Invalid status. Choices: {valid}'},
                            status=status.HTTP_400_BAD_REQUEST)
        visit.advance(to, user=request.user)
        return Response(VisitSerializer(visit).data)

    # ── Vitals ────────────────────────────────────────────────────────────────
    @action(detail=True, methods=['post', 'get'])
    def vitals(self, request, pk=None):
        visit = self.get_object()
        if request.method == 'GET':
            try:
                return Response(VitalsSerializer(visit.vitals).data)
            except Vitals.DoesNotExist:
                return Response({'detail': 'No vitals recorded'}, status=404)

        # POST — create or update
        try:
            instance = visit.vitals
            s = VitalsSerializer(instance, data=request.data, partial=True)
        except Vitals.DoesNotExist:
            s = VitalsSerializer(data={**request.data, 'visit': visit.id})

        s.is_valid(raise_exception=True)
        s.save(visit=visit, recorded_by=request.user)
        # Advance visit to triage if still registered
        if visit.status == 'registered':
            visit.advance('triage', request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    # ── Diagnosis ─────────────────────────────────────────────────────────────
    @action(detail=True, methods=['post', 'get'])
    def diagnosis(self, request, pk=None):
        visit = self.get_object()
        if request.method == 'GET':
            try:
                return Response(DiagnosisSerializer(visit.diagnosis).data)
            except Diagnosis.DoesNotExist:
                return Response({'detail': 'No diagnosis yet'}, status=404)

        try:
            instance = visit.diagnosis
            s = DiagnosisSerializer(instance, data=request.data, partial=True)
        except Diagnosis.DoesNotExist:
            s = DiagnosisSerializer(data={**request.data, 'visit': visit.id})

        s.is_valid(raise_exception=True)
        dx = s.save(visit=visit, doctor=request.user)
        # Auto-advance visit status
        if request.data.get('send_to_lab') and visit.status == 'consultation':
            visit.advance('lab', request.user)
        elif visit.status == 'consultation':
            visit.advance('prescription', request.user)
        return Response(DiagnosisSerializer(dx).data, status=status.HTTP_201_CREATED)

    # ── Billing event ─────────────────────────────────────────────────────────
    @action(detail=True, methods=['post', 'get'])
    def bill(self, request, pk=None):
        visit = self.get_object()
        if request.method == 'GET':
            return Response(
                VisitBillingEventSerializer(visit.billing_events.all(), many=True).data
            )
        s = VisitBillingEventSerializer(data={**request.data, 'visit': visit.id})
        s.is_valid(raise_exception=True)
        s.save(visit=visit, created_by=request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    # ── Print report ──────────────────────────────────────────────────────────
    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        visit = self.get_object()
        return Response(VisitReportSerializer(visit).data)

    # ── Active visits (not completed / cancelled) ─────────────────────────────
    @action(detail=False, methods=['get'])
    def active(self, request):
        qs = self.get_queryset().exclude(status__in=['completed', 'cancelled'])
        return Response(VisitSerializer(qs, many=True).data)

    # ── Today's visits ────────────────────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        qs = self.get_queryset().filter(registered_at__date=today)
        return Response(VisitSerializer(qs, many=True).data)


class VitalsViewSet(viewsets.ModelViewSet):
    queryset         = Vitals.objects.select_related('visit__patient', 'recorded_by')
    serializer_class = VitalsSerializer
    filterset_fields = ['visit']

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class DiagnosisViewSet(viewsets.ModelViewSet):
    queryset         = Diagnosis.objects.select_related('visit__patient', 'doctor')
    serializer_class = DiagnosisSerializer
    filterset_fields = ['visit']

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user)


class VisitBillingEventViewSet(viewsets.ModelViewSet):
    queryset         = VisitBillingEvent.objects.select_related('visit', 'created_by')
    serializer_class = VisitBillingEventSerializer
    filterset_fields = ['visit', 'stage']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
