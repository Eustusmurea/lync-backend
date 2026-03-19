from rest_framework import serializers
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
