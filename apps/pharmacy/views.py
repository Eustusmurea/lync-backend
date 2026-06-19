from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from apps.users.permissions import RBACMixin
from .models import (DrugCategory, Drug, DrugStockTransaction,
                     Prescription, PrescriptionItem, Dispense, OTCSale)
from .serializers import (
    DrugCategorySerializer, DrugSerializer, DrugStockTransactionSerializer,
    PrescriptionSerializer, PrescriptionCreateSerializer,
    DispenseSerializer, DispenseCreateSerializer,
    OTCSaleSerializer, OTCSaleCreateSerializer,
)


class DrugCategoryViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset         = DrugCategory.objects.all()
    serializer_class = DrugCategorySerializer
    rbac_map = {a: 'pharmacy.view' for a in ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy']}


class DrugViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset         = Drug.objects.select_related('category').filter(is_active=True)
    serializer_class = DrugSerializer
    search_fields    = ['name', 'generic_name', 'brand_name', 'barcode']
    filterset_fields = ['category', 'form', 'controlled']

    rbac_map = {
        'list': 'pharmacy.view',
        'retrieve': 'pharmacy.view',
        'create': 'inventory.manage',
        'update': 'inventory.manage',
        'partial_update': 'inventory.manage',
        'destroy': 'inventory.manage',
        'low_stock': 'pharmacy.view',
        'out_of_stock': 'pharmacy.view',
        'adjust_stock': 'inventory.manage',
        'summary': 'pharmacy.view',
    }

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        drugs = [d for d in self.get_queryset() if d.stock_level in ('low', 'out')]
        return Response(DrugSerializer(drugs, many=True).data)

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        drugs = [d for d in self.get_queryset() if d.stock_level == 'out']
        return Response(DrugSerializer(drugs, many=True).data)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        drug    = self.get_object()
        qty     = float(request.data.get('quantity', 0))
        t_type  = request.data.get('type', 'receive')
        notes   = request.data.get('notes', '')
        before  = drug.stock_quantity

        if t_type == 'receive':
            drug.stock_quantity += qty
        elif t_type == 'adjust':
            drug.stock_quantity = qty
        elif t_type == 'expire':
            drug.stock_quantity = max(0, drug.stock_quantity - qty)
        else:
            drug.stock_quantity = max(0, drug.stock_quantity - qty)
        drug.save()

        DrugStockTransaction.objects.create(
            drug=drug, transaction_type=t_type, quantity=qty,
            quantity_before=before, quantity_after=drug.stock_quantity,
            performed_by=request.user, notes=notes,
        )
        return Response(DrugSerializer(drug).data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = Drug.objects.filter(is_active=True)
        drugs = list(qs)
        return Response({
            'total_drugs':    qs.count(),
            'low_stock':      sum(1 for d in drugs if d.stock_level == 'low'),
            'out_of_stock':   sum(1 for d in drugs if d.stock_level == 'out'),
            'controlled':     qs.filter(controlled=True).count(),
            'total_value':    float(sum(
                d.stock_quantity * float(d.unit_price) for d in drugs
            )),
        })


class DrugStockTransactionViewSet(RBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset         = DrugStockTransaction.objects.select_related('drug', 'performed_by')
    serializer_class = DrugStockTransactionSerializer
    filterset_fields = ['drug', 'transaction_type']
    rbac_map = {'list': 'pharmacy.view', 'retrieve': 'pharmacy.view'}


class PrescriptionViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = Prescription.objects.select_related(
        'patient', 'prescribed_by'
    ).prefetch_related('items__drug')
    search_fields    = ['rx_number', 'patient__first_name', 'patient__last_name', 'patient__mrn']
    filterset_fields = ['status', 'patient']

    rbac_map = {
        'list': 'pharmacy.view',
        'retrieve': 'pharmacy.view',
        'create': 'clinical.prescribe',
        'update': 'pharmacy.view',
        'partial_update': 'pharmacy.view',
        'destroy': 'pharmacy.view',
        'cancel': 'pharmacy.view',
        'active': 'pharmacy.view',
    }

    def get_serializer_class(self):
        return PrescriptionCreateSerializer if self.action == 'create' else PrescriptionSerializer

    def perform_create(self, serializer):
        serializer.save(prescribed_by=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        rx = self.get_object()
        rx.status = 'cancelled'
        rx.save()
        return Response(PrescriptionSerializer(rx).data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        qs = self.get_queryset().filter(status__in=['active', 'partial'])
        return Response(PrescriptionSerializer(qs, many=True).data)


class DispenseViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = Dispense.objects.select_related(
        'prescription__patient', 'dispensed_by'
    ).prefetch_related('items__drug')
    search_fields    = ['dispense_id', 'prescription__rx_number',
                        'prescription__patient__first_name',
                        'prescription__patient__last_name']
    filterset_fields = ['prescription']

    rbac_map = {
        'list': 'pharmacy.dispense',
        'retrieve': 'pharmacy.dispense',
        'create': 'pharmacy.dispense',
        'update': 'pharmacy.dispense',
        'partial_update': 'pharmacy.dispense',
        'destroy': 'pharmacy.dispense',
    }

    def get_serializer_class(self):
        return DispenseCreateSerializer if self.action == 'create' else DispenseSerializer

    def perform_create(self, serializer):
        dispense = serializer.save(dispensed_by=self.request.user)
        rx = dispense.prescription
        if rx.visit_id:
            from apps.visits.workflow import sync_visit_after_dispense
            sync_visit_after_dispense(rx.visit)


class OTCSaleViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = OTCSale.objects.select_related('patient', 'dispensed_by').prefetch_related('items__drug')
    search_fields = ['sale_id', 'patient__first_name', 'patient__last_name', 'patient__mrn']
    filterset_fields = ['patient', 'payment_method']

    rbac_map = {
        'list': 'pharmacy.otc',
        'retrieve': 'pharmacy.otc',
        'create': 'pharmacy.otc',
        'update': 'pharmacy.otc',
        'partial_update': 'pharmacy.otc',
        'destroy': 'pharmacy.otc',
    }

    def get_serializer_class(self):
        return OTCSaleCreateSerializer if self.action == 'create' else OTCSaleSerializer

    def perform_create(self, serializer):
        serializer.save(dispensed_by=self.request.user)
