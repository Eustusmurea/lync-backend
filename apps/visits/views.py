from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from apps.users.permissions import RBACMixin
from .models import Visit, Vitals, Diagnosis, VisitBillingEvent
from .serializers import (
    VisitSerializer, VisitReportSerializer,
    VitalsSerializer, DiagnosisSerializer,
    VisitBillingEventSerializer,
)
from .pdf_service import render_visit_pdf
from . import workflow


class VisitViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = Visit.objects.select_related(
        'patient', 'registered_by', 'attending_doctor'
    ).prefetch_related('billing_events', 'test_orders', 'prescriptions')
    serializer_class = VisitSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['status', 'patient']
    search_fields    = ['visit_number', 'patient__first_name',
                        'patient__last_name', 'patient__mrn']

    rbac_map = {
        'list': 'visits.view',
        'retrieve': 'visits.view',
        'create': 'visits.create',
        'update': 'visits.create',
        'partial_update': 'visits.create',
        'destroy': 'visits.create',
        'advance': 'visits.create',
        'vitals': 'clinical.vitals',
        'diagnosis': 'clinical.diagnosis',
        'consultation': 'clinical.consultation',
        'lab_orders': 'clinical.lab_order',
        'skip_lab': 'clinical.lab_order',
        'prescription': 'clinical.prescribe',
        'generate_invoice': 'billing.invoice',
        'bill': 'billing.view',
        'report': 'reports.print',
        'pdf': 'reports.print',
        'active': 'visits.view',
        'today': 'visits.view',
        'queue': 'visits.view',
    }

    def perform_create(self, serializer):
        visit = serializer.save(registered_by=self.request.user)
        VisitBillingEvent.objects.create(
            visit=visit,
            stage='registration',
            description='Registration fee',
            amount=500,
            created_by=self.request.user,
        )

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

    @action(detail=True, methods=['post', 'get'])
    def vitals(self, request, pk=None):
        visit = self.get_object()
        if request.method == 'GET':
            try:
                return Response(VitalsSerializer(visit.vitals).data)
            except Vitals.DoesNotExist:
                return Response({'detail': 'No vitals recorded'}, status=404)

        err = workflow.assert_stage(visit, 'vitals')
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = visit.vitals
            s = VitalsSerializer(instance, data=request.data, partial=True)
        except Vitals.DoesNotExist:
            s = VitalsSerializer(data={**request.data, 'visit': visit.id})

        s.is_valid(raise_exception=True)
        s.save(visit=visit, recorded_by=request.user)
        if visit.status == 'registered':
            visit.advance('triage', request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'get'])
    def diagnosis(self, request, pk=None):
        visit = self.get_object()
        if request.method == 'GET':
            try:
                return Response(DiagnosisSerializer(visit.diagnosis).data)
            except Diagnosis.DoesNotExist:
                return Response({'detail': 'No diagnosis yet'}, status=404)

        err = workflow.assert_stage(visit, 'diagnosis')
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = visit.diagnosis
            s = DiagnosisSerializer(instance, data=request.data, partial=True)
        except Diagnosis.DoesNotExist:
            s = DiagnosisSerializer(data={**request.data, 'visit': visit.id})

        s.is_valid(raise_exception=True)
        dx = s.save(visit=visit, doctor=request.user)
        VisitBillingEvent.objects.get_or_create(
            visit=visit,
            stage='consultation',
            description='Consultation & diagnosis',
            defaults={'amount': 1500, 'created_by': request.user},
        )
        return Response(DiagnosisSerializer(dx).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def consultation(self, request, pk=None):
        visit = self.get_object()
        err = workflow.assert_stage(visit, 'consultation')
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        if 'chief_complaint' in request.data:
            visit.chief_complaint = request.data['chief_complaint']
        if 'notes' in request.data:
            visit.notes = request.data['notes']
        visit.save()
        if visit.status in ('registered', 'triage'):
            visit.advance('consultation', request.user)
        return Response(VisitSerializer(visit).data)

    @action(detail=True, methods=['post'])
    def skip_lab(self, request, pk=None):
        """Clinician marks visit as not requiring lab — proceed to diagnosis."""
        visit = self.get_object()
        err = workflow.assert_stage(visit, 'skip_lab')
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
        visit.requires_lab = False
        visit.advance('results_ready', request.user)
        return Response(VisitSerializer(visit).data)

    @action(detail=True, methods=['post'])
    def lab_orders(self, request, pk=None):
        from apps.samples.models import Sample
        from apps.tests.models import TestPanel, TestOrder
        from apps.tests.serializers import TestOrderSerializer

        visit = self.get_object()
        err = workflow.assert_stage(visit, 'lab_orders')
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        panel_ids = request.data.get('panel_ids', [])
        if not panel_ids:
            return Response({'error': 'panel_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now()
        sample = Sample.objects.filter(
            patient=visit.patient,
            collected_at__date=today.date(),
        ).first()
        if not sample:
            sample = Sample.objects.create(
                patient=visit.patient,
                sample_type=request.data.get('sample_type', 'blood'),
                collected_at=today,
                received_by=request.user,
            )

        orders = []
        total_lab = 0
        for panel_id in panel_ids:
            try:
                panel = TestPanel.objects.get(pk=panel_id, is_active=True)
            except TestPanel.DoesNotExist:
                continue
            order = TestOrder.objects.create(
                sample=sample,
                visit=visit,
                panel=panel,
                ordered_by=request.user,
            )
            orders.append(order)
            total_lab += float(panel.price)

        if orders:
            visit.requires_lab = True
            visit.advance('lab', request.user)
            VisitBillingEvent.objects.create(
                visit=visit,
                stage='lab',
                description=f'Laboratory tests ({len(orders)} panel(s))',
                amount=total_lab or len(orders) * 800,
                created_by=request.user,
            )

        return Response(TestOrderSerializer(orders, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'get'])
    def prescription(self, request, pk=None):
        from apps.pharmacy.models import Prescription, PrescriptionItem
        from apps.pharmacy.serializers import PrescriptionSerializer

        visit = self.get_object()
        if request.method == 'GET':
            rx = visit.prescriptions.order_by('-prescribed_at').first()
            if not rx:
                return Response({'detail': 'No prescription yet'}, status=404)
            return Response(PrescriptionSerializer(rx).data)

        err = workflow.assert_stage(visit, 'prescription')
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'error': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)

        dx_text = ''
        if hasattr(visit, 'diagnosis'):
            dx_text = visit.diagnosis.diagnosis

        rx = Prescription.objects.create(
            patient=visit.patient,
            visit=visit,
            prescribed_by=request.user,
            diagnosis=dx_text,
            notes=request.data.get('notes', ''),
        )
        for item in items_data:
            PrescriptionItem.objects.create(prescription=rx, **item)

        visit.advance('pharmacy', request.user)
        VisitBillingEvent.objects.create(
            visit=visit,
            stage='pharmacy',
            description=f'Prescription {rx.rx_number}',
            amount=request.data.get('amount', 0) or sum(
                float(i.get('quantity', 0)) * 100 for i in items_data
            ),
            created_by=request.user,
        )
        return Response(PrescriptionSerializer(rx).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def generate_invoice(self, request, pk=None):
        from apps.billing.models import Invoice, InvoiceItem

        visit = self.get_object()
        existing = visit.invoices.exclude(status='void').first()
        if existing:
            return Response({'invoice_id': existing.id, 'invoice_number': existing.invoice_number})

        inv = Invoice.objects.create(
            patient=visit.patient,
            visit=visit,
            created_by=request.user,
            status='issued',
            issued_at=timezone.now(),
        )
        for event in visit.billing_events.all():
            InvoiceItem.objects.create(
                invoice=inv,
                description=event.description,
                quantity=1,
                unit_price=event.amount,
            )
        inv.refresh_from_db()
        return Response({
            'invoice_id': inv.id,
            'invoice_number': inv.invoice_number,
            'total': str(inv.total),
            'balance': str(inv.balance),
        }, status=status.HTTP_201_CREATED)

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

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        visit = self.get_object()
        return Response(VisitReportSerializer(visit).data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        visit = self.get_object()
        try:
            pdf_bytes = render_visit_pdf(visit)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        filename = f'{visit.visit_number}_patient_file.pdf'
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'])
    def active(self, request):
        qs = self.get_queryset().exclude(status__in=['completed', 'cancelled'])
        return Response(VisitSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        qs = self.get_queryset().filter(registered_at__date=today)
        return Response(VisitSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def queue(self, request):
        """Visits filtered by workflow stage for role-specific queues."""
        stage = request.query_params.get('stage')
        qs = self.get_queryset().exclude(status__in=['completed', 'cancelled'])
        if stage:
            qs = qs.filter(status=stage)
        return Response(VisitSerializer(qs, many=True).data)


class VitalsViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset         = Vitals.objects.select_related('visit__patient', 'recorded_by')
    serializer_class = VitalsSerializer
    filterset_fields = ['visit']
    rbac_map = {
        'list': 'clinical.vitals',
        'retrieve': 'clinical.vitals',
        'create': 'clinical.vitals',
        'update': 'clinical.vitals',
        'partial_update': 'clinical.vitals',
        'destroy': 'clinical.vitals',
    }

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class DiagnosisViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset         = Diagnosis.objects.select_related('visit__patient', 'doctor')
    serializer_class = DiagnosisSerializer
    filterset_fields = ['visit']
    rbac_map = {
        'list': 'clinical.diagnosis',
        'retrieve': 'clinical.diagnosis',
        'create': 'clinical.diagnosis',
        'update': 'clinical.diagnosis',
        'partial_update': 'clinical.diagnosis',
        'destroy': 'clinical.diagnosis',
    }

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user)


class VisitBillingEventViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset         = VisitBillingEvent.objects.select_related('visit', 'created_by')
    serializer_class = VisitBillingEventSerializer
    filterset_fields = ['visit', 'stage']
    rbac_map = {
        'list': 'billing.view',
        'retrieve': 'billing.view',
        'create': 'billing.view',
        'update': 'billing.view',
        'partial_update': 'billing.view',
        'destroy': 'billing.view',
    }

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
