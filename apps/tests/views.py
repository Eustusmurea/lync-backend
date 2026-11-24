from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.users.permissions import RBACMixin
from .flagging import apply_numeric_flag, sync_order_review_status
from .models import TestPanel, TestParameter, TestOrder, TestResult, ResultAmendment
from .serializers import (
    TestPanelSerializer,
    TestParameterSerializer,
    TestOrderSerializer,
    TestResultSerializer,
)
from .filters import TestOrderFilter


class TestPanelViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = TestPanel.objects.filter(is_active=True)
    serializer_class = TestPanelSerializer
    search_fields = ['name', 'code']
    rbac_map = {
        'list': 'lab.view',
        'retrieve': 'lab.view',
        'create': 'lab.panels_manage',
        'update': 'lab.panels_manage',
        'partial_update': 'lab.panels_manage',
        'destroy': 'lab.panels_manage',
    }


class TestOrderViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = TestOrder.objects.select_related(
        'sample__patient', 'panel', 'ordered_by', 'assigned_to'
    ).prefetch_related('results__parameter', 'results__amendments__amended_by', 'panel__parameters')
    serializer_class = TestOrderSerializer
    filterset_class = TestOrderFilter
    search_fields = ['order_id', 'sample__patient__first_name', 'sample__patient__last_name', 'sample__patient__mrn']
    ordering_fields = ['ordered_at', 'status', 'panel__name']

    rbac_map = {
        'list': 'lab.view',
        'retrieve': 'lab.view',
        'create': 'clinical.lab_order',
        'update': 'lab.results',
        'partial_update': 'lab.results',
        'destroy': 'lab.panels_manage',
        'start': 'lab.results',
        'complete': 'lab.results',
        'notify_critical': 'lab.results',
        'overdue': 'lab.view',
        'critical': 'lab.view',
        'cancel': 'clinical.lab_order',
    }

    def perform_create(self, serializer):
        serializer.save(ordered_by=self.request.user)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        order = self.get_object()
        order.status = 'processing'
        order.started_at = timezone.now()
        order.assigned_to = request.user
        order.save()
        return Response(TestOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        if order.status == 'cancelled':
            return Response(
                {'detail': 'A cancelled order cannot be completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        expected = order.panel.parameters.count()
        results = list(order.results.all())
        if expected == 0 or len(results) < expected or any(r.verified_at is None for r in results):
            return Response(
                {'detail': 'Every parameter must be entered and authorized before release.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = 'complete'
        order.completed_at = timezone.now()
        order.save()
        if order.visit_id:
            from apps.visits.workflow import sync_visit_after_lab
            sync_visit_after_lab(order.visit)
        return Response(TestOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status == 'complete':
            return Response(
                {'detail': 'A completed order cannot be cancelled. Amend the authorized result instead.'},
                status=status.HTTP_409_CONFLICT,
            )
        if order.results.filter(verified_at__isnull=False).exists():
            return Response(
                {'detail': 'An order with an authorized result cannot be cancelled.'},
                status=status.HTTP_409_CONFLICT,
            )
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response({'detail': 'A cancellation reason is required.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        note = f'Cancelled: {reason}'
        order.notes = f'{order.notes}\n{note}'.strip() if order.notes else note
        order.save()
        return Response(TestOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def notify_critical(self, request, pk=None):
        order = self.get_object()
        order.critical_notified = True
        order.critical_notified_at = timezone.now()
        order.save()
        return Response({'status': 'notification recorded', 'order_id': order.order_id})

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        overdue = [o for o in self.get_queryset() if o.is_overdue]
        serializer = self.get_serializer(overdue, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def critical(self, request):
        critical = self.get_queryset().filter(is_critical=True, critical_notified=False)
        serializer = self.get_serializer(critical, many=True)
        return Response(serializer.data)


class TestParameterViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = TestParameter.objects.select_related('panel')
    serializer_class = TestParameterSerializer
    filterset_fields = ['panel']
    rbac_map = {
        'list': 'lab.view',
        'retrieve': 'lab.view',
        'create': 'lab.panels_manage',
        'update': 'lab.panels_manage',
        'partial_update': 'lab.panels_manage',
        'destroy': 'lab.panels_manage',
    }


class TestResultViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = TestResult.objects.select_related(
        'order', 'parameter', 'entered_by', 'verified_by'
    ).prefetch_related('amendments')
    serializer_class = TestResultSerializer

    rbac_map = {
        'list': 'lab.view',
        'retrieve': 'lab.view',
        'create': 'lab.results',
        'update': 'lab.results',
        'partial_update': 'lab.results',
        'destroy': 'lab.results',
        'verify': 'lab.authorize',
        'amend': 'lab.authorize',
    }

    def _reject_if_authorized(self, result):
        if result.verified_at:
            return Response(
                {'detail': 'An authorized result cannot be overwritten. Record an amendment.'},
                status=status.HTTP_409_CONFLICT,
            )
        return None

    def update(self, request, *args, **kwargs):
        blocked = self._reject_if_authorized(self.get_object())
        if blocked:
            return blocked
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        blocked = self._reject_if_authorized(self.get_object())
        if blocked:
            return blocked
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        blocked = self._reject_if_authorized(self.get_object())
        if blocked:
            return blocked
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        result = serializer.save(entered_by=self.request.user)
        apply_numeric_flag(result)
        sync_order_review_status(result.order)

    def perform_update(self, serializer):
        result = serializer.save()
        apply_numeric_flag(result)
        sync_order_review_status(result.order)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        result = self.get_object()
        if result.entered_by_id and result.entered_by_id == request.user.id and request.user.role != 'admin':
            return Response(
                {'detail': 'The person who entered a result cannot authorize it.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        result.verified_by = request.user
        result.verified_at = timezone.now()
        result.save(update_fields=['verified_by', 'verified_at'])
        return Response(TestResultSerializer(result).data)

    @action(detail=True, methods=['post'])
    def amend(self, request, pk=None):
        result = self.get_object()
        if not result.verified_at:
            return Response(
                {'detail': 'Only an authorized result can be amended. Edit it before authorization.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_value = str(request.data.get('value') or '').strip()
        reason = str(request.data.get('reason') or '').strip()
        if not new_value or not reason:
            return Response(
                {'detail': 'A new value and a reason are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ResultAmendment.objects.create(
            result=result,
            previous_value=result.value,
            previous_numeric_value=result.numeric_value,
            previous_flag=result.flag,
            new_value=new_value,
            reason=reason,
            amended_by=request.user,
        )
        result.value = new_value
        raw_numeric = request.data.get('numeric_value', None)
        if raw_numeric in (None, ''):
            try:
                result.numeric_value = float(new_value)
            except (TypeError, ValueError):
                result.numeric_value = None
        else:
            result.numeric_value = float(raw_numeric)
        result.comment = reason
        result.verified_by = None
        result.verified_at = None
        result.save()
        apply_numeric_flag(result)
        order = result.order
        if order.status == 'complete':
            order.status = 'review'
            order.completed_at = None
            order.save(update_fields=['status', 'completed_at'])
        else:
            sync_order_review_status(order)
        result.refresh_from_db()
        return Response(TestResultSerializer(result).data)
