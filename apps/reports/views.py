from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import HasPermission
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta

from apps.tests.models import TestOrder, TestResult
from apps.samples.models import Sample
from apps.inventory.models import Reagent


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission('dashboard.view')]

    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        orders_today = TestOrder.objects.filter(ordered_at__date=today)
        orders_yesterday = TestOrder.objects.filter(ordered_at__date=today - timedelta(days=1))

        completed_today = orders_today.filter(status='complete').count()
        completed_yesterday = orders_yesterday.filter(status='complete').count()

        pct_change = 0
        if completed_yesterday > 0:
            pct_change = round(((completed_today - completed_yesterday) / completed_yesterday) * 100, 1)

        pending = TestOrder.objects.filter(status__in=['pending', 'processing']).count()
        overdue = [o for o in TestOrder.objects.filter(status__in=['pending', 'processing']) if o.is_overdue]
        critical_unnotified = TestOrder.objects.filter(is_critical=True, critical_notified=False).count()
        low_stock = sum(1 for r in Reagent.objects.filter(is_active=True) if r.stock_level == 'low')

        # TAT for completed orders in the last 7 days
        recent_completed = TestOrder.objects.filter(
            status='complete',
            ordered_at__date__gte=week_ago,
            completed_at__isnull=False
        )

        tat_data = []
        for order in recent_completed:
            minutes = order.turnaround_minutes
            if minutes:
                tat_data.append({'panel': order.panel.name, 'minutes': minutes})

        return Response({
            'orders_today': orders_today.count(),
            'completed_today': completed_today,
            'completed_change_pct': pct_change,
            'pending_results': pending,
            'overdue_count': len(overdue),
            'critical_unnotified': critical_unnotified,
            'low_stock_count': low_stock,
            'tat_data': tat_data,
        })


class TestVolumeReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission('lab.view')]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        start = timezone.now().date() - timedelta(days=days)

        volume = (
            TestOrder.objects
            .filter(ordered_at__date__gte=start)
            .extra(select={'day': 'DATE(ordered_at)'})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        by_panel = (
            TestOrder.objects
            .filter(ordered_at__date__gte=start)
            .values('panel__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        return Response({
            'daily_volume': list(volume),
            'by_panel': list(by_panel),
            'total': TestOrder.objects.filter(ordered_at__date__gte=start).count(),
        })


class InventoryReportView(APIView):
    permission_classes = [IsAuthenticated, HasPermission('inventory.view')]

    def get(self, request):
        reagents = Reagent.objects.filter(is_active=True)
        low = [r for r in reagents if r.stock_level == 'low']
        warning = [r for r in reagents if r.stock_level == 'warning']

        from apps.inventory.views import ReagentSerializer
        return Response({
            'total_reagents': reagents.count(),
            'low_stock': ReagentSerializer(low, many=True).data,
            'warning_stock': ReagentSerializer(warning, many=True).data,
        })
