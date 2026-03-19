from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Reagent, ReagentCategory, StockTransaction


class ReagentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReagentCategory
        fields = '__all__'


class ReagentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_level = serializers.CharField(read_only=True)
    stock_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = Reagent
        fields = '__all__'


class StockTransactionSerializer(serializers.ModelSerializer):
    reagent_name = serializers.CharField(source='reagent.name', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)

    class Meta:
        model = StockTransaction
        fields = '__all__'
        read_only_fields = ['quantity_before', 'quantity_after', 'performed_by']


class ReagentViewSet(viewsets.ModelViewSet):
    queryset = Reagent.objects.select_related('category').filter(is_active=True)
    serializer_class = ReagentSerializer
    search_fields = ['name', 'catalog_number', 'manufacturer']
    filterset_fields = ['category', 'unit']

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


class StockTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockTransaction.objects.select_related('reagent', 'performed_by')
    serializer_class = StockTransactionSerializer
    filterset_fields = ['reagent', 'transaction_type']
