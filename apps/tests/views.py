from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from apps.users.permissions import RBACMixin
from .models import TestPanel, TestOrder, TestResult
from .serializers import TestPanelSerializer, TestOrderSerializer, TestResultSerializer
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
    ).prefetch_related('results__parameter')
    serializer_class = TestOrderSerializer
    filterset_class = TestOrderFilter
    search_fields = ['order_id', 'sample__patient__first_name', 'sample__patient__last_name', 'sample__patient__mrn']
    ordering_fields = ['ordered_at', 'status', 'panel__name']

    rbac_map = {
        'list': 'lab.view',
        'retrieve': 'lab.view',
        'create': 'lab.view',
        'update': 'lab.view',
        'partial_update': 'lab.view',
        'destroy': 'lab.view',
        'start': 'lab.results',
        'complete': 'lab.results',
        'notify_critical': 'lab.results',
        'overdue': 'lab.view',
        'critical': 'lab.view',
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
        order.status = 'complete'
        order.completed_at = timezone.now()
        order.save()
        if order.visit_id:
            from apps.visits.workflow import sync_visit_after_lab
            sync_visit_after_lab(order.visit)
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


class TestResultViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = TestResult.objects.select_related('order', 'parameter', 'entered_by', 'verified_by')
    serializer_class = TestResultSerializer

    rbac_map = {
        'list': 'lab.view',
        'retrieve': 'lab.view',
        'create': 'lab.results',
        'update': 'lab.results',
        'partial_update': 'lab.results',
        'destroy': 'lab.results',
        'verify': 'lab.results',
    }

    def perform_create(self, serializer):
        result = serializer.save(entered_by=self.request.user)
        # Auto-flag based on reference ranges
        param = result.parameter
        if result.numeric_value is not None:
            if param.critical_high and result.numeric_value > param.critical_high:
                result.flag = 'critical_high'
                result.order.is_critical = True
                result.order.save()
            elif param.critical_low and result.numeric_value < param.critical_low:
                result.flag = 'critical_low'
                result.order.is_critical = True
                result.order.save()
            elif param.ref_range_high and result.numeric_value > param.ref_range_high:
                result.flag = 'high'
            elif param.ref_range_low and result.numeric_value < param.ref_range_low:
                result.flag = 'low'
            result.save()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        result = self.get_object()
        result.verified_by = request.user
        result.verified_at = timezone.now()
        result.save()
        return Response(TestResultSerializer(result).data)
