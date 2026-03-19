from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Count
from django_filters.rest_framework import DjangoFilterBackend
from .models import InsuranceProvider, Invoice, InvoiceItem, Payment
from .serializers import (
    InsuranceProviderSerializer, InvoiceSerializer,
    InvoiceCreateSerializer, InvoiceItemSerializer, PaymentSerializer,
)


class InsuranceProviderViewSet(viewsets.ModelViewSet):
    queryset         = InsuranceProvider.objects.filter(is_active=True)
    serializer_class = InsuranceProviderSerializer
    search_fields    = ['name', 'code']


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related(
        'patient', 'insurance', 'created_by'
    ).prefetch_related('items__test_order', 'payments__received_by')
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['status', 'patient', 'insurance']
    search_fields    = ['invoice_number', 'patient__first_name', 'patient__last_name', 'patient__mrn']

    def get_serializer_class(self):
        return InvoiceCreateSerializer if self.action == 'create' else InvoiceSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        inv = self.get_object()
        if inv.status == 'draft':
            inv.status    = 'issued'
            inv.issued_at = timezone.now()
            inv.save()
        return Response(InvoiceSerializer(inv).data)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        inv = self.get_object()
        inv.status = 'void'
        inv.save()
        return Response(InvoiceSerializer(inv).data)

    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        inv = self.get_object()
        s   = PaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(invoice=inv, received_by=request.user)
        inv.refresh_from_db()
        return Response(InvoiceSerializer(inv).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        inv  = self.get_object()
        data = {**request.data, 'invoice': inv.id}
        s    = InvoiceItemSerializer(data=data)
        s.is_valid(raise_exception=True)
        s.save()
        inv.refresh_from_db()
        return Response(InvoiceSerializer(inv).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        today       = timezone.now().date()
        month_start = today.replace(day=1)
        qs          = Invoice.objects.all()
        return Response({
            'total_revenue': float(qs.filter(status='paid').aggregate(t=Sum('total'))['t'] or 0),
            'month_revenue': float(qs.filter(status='paid', issued_at__date__gte=month_start).aggregate(t=Sum('total'))['t'] or 0),
            'outstanding':   float(qs.filter(status__in=['issued', 'partial', 'overdue']).aggregate(t=Sum('balance'))['t'] or 0),
            'overdue_count': qs.filter(status='overdue').count(),
            'draft_count':   qs.filter(status='draft').count(),
            'by_status':     list(qs.values('status').annotate(count=Count('id'), total=Sum('total')).order_by('status')),
        })


class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset         = InvoiceItem.objects.select_related('invoice', 'test_order')
    serializer_class = InvoiceItemSerializer
    filterset_fields = ['invoice']


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset         = Payment.objects.select_related('invoice', 'received_by')
    serializer_class = PaymentSerializer
    filterset_fields = ['invoice', 'method']
