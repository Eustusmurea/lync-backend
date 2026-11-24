from rest_framework import serializers
from .models import Reagent, ReagentCategory, StockTransaction
import uuid


class ReagentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReagentCategory
        fields = '__all__'


class ReagentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    stock_level = serializers.CharField(read_only=True)
    stock_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = Reagent
        fields = '__all__'


class ReagentCreateSerializer(serializers.ModelSerializer):
    """Accepts optional category_name string; auto-generates catalog_number if omitted."""

    category_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Reagent
        fields = [
            'name', 'catalog_number', 'category', 'category_name',
            'manufacturer', 'supplier', 'unit', 'stock_quantity',
            'reorder_level', 'max_stock', 'storage_condition',
            'expiry_date', 'location', 'notes', 'is_active',
        ]

    def validate(self, attrs):
        if not attrs.get('catalog_number'):
            attrs['catalog_number'] = f'CAT-{uuid.uuid4().hex[:8].upper()}'
        cat_name = (attrs.get('category_name') or '').strip()
        if cat_name and not attrs.get('category'):
            cat, _ = ReagentCategory.objects.get_or_create(name=cat_name)
            attrs['category'] = cat
        attrs.pop('category_name', None)
        return attrs


class StockTransactionSerializer(serializers.ModelSerializer):
    reagent_name = serializers.CharField(source='reagent.name', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)

    class Meta:
        model = StockTransaction
        fields = '__all__'
        read_only_fields = ['quantity_before', 'quantity_after', 'performed_by']
