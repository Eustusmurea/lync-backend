from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.users.permissions import RBACMixin
from .models import Reagent, ReagentCategory, StockTransaction
from .serializers import (
    ReagentSerializer,
    ReagentCreateSerializer,
    ReagentCategorySerializer,
    StockTransactionSerializer,
)


class ReagentCategoryViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = ReagentCategory.objects.all()
    serializer_class = ReagentCategorySerializer
    rbac_map = {a: 'inventory.manage' for a in ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy']}


class ReagentViewSet(RBACMixin, viewsets.ModelViewSet):
    queryset = Reagent.objects.select_related('category').filter(is_active=True)
    serializer_class = ReagentSerializer
    search_fields = ['name', 'catalog_number', 'manufacturer']
    filterset_fields = ['category', 'unit']

    rbac_map = {
        'list': 'inventory.view',
        'retrieve': 'inventory.view',
        'create': 'inventory.manage',
        'update': 'inventory.manage',
        'partial_update': 'inventory.manage',
        'destroy': 'inventory.manage',
        'low_stock': 'inventory.view',
        'adjust_stock': 'inventory.manage',
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return ReagentCreateSerializer
        return ReagentSerializer

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        low = [r for r in self.get_queryset() if r.stock_level == 'low']
        return Response(ReagentSerializer(low, many=True).data)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        reagent = self.get_object()
        qty = float(request.data.get('quantity', 0))
        t_type = request.data.get('type', 'adjust')
        notes = request.data.get('notes', '')

        before = reagent.stock_quantity
        if t_type == 'receive':
            reagent.stock_quantity += qty
        elif t_type == 'consume':
            reagent.stock_quantity = max(0, reagent.stock_quantity - qty)
        else:
            reagent.stock_quantity = qty
        reagent.save()

        StockTransaction.objects.create(
            reagent=reagent,
            transaction_type=t_type,
            quantity=qty,
            quantity_before=before,
            quantity_after=reagent.stock_quantity,
            performed_by=request.user,
            notes=notes,
        )
        return Response(ReagentSerializer(reagent).data)


class StockTransactionViewSet(RBACMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockTransaction.objects.select_related('reagent', 'performed_by')
    serializer_class = StockTransactionSerializer
    filterset_fields = ['reagent', 'transaction_type']
    rbac_map = {'list': 'inventory.view', 'retrieve': 'inventory.view'}
