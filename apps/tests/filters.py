import django_filters
from .models import TestOrder


class TestOrderFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    panel = django_filters.NumberFilter(field_name='panel__id')
    is_critical = django_filters.BooleanFilter(field_name='is_critical')
    ordered_after = django_filters.DateTimeFilter(field_name='ordered_at', lookup_expr='gte')
    ordered_before = django_filters.DateTimeFilter(field_name='ordered_at', lookup_expr='lte')

    class Meta:
        model = TestOrder
        fields = ['status', 'panel', 'is_critical']
