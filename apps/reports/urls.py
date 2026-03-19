from django.urls import path
from .views import DashboardStatsView, TestVolumeReportView, InventoryReportView

urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('test-volume/', TestVolumeReportView.as_view(), name='test-volume'),
    path('inventory/', InventoryReportView.as_view(), name='inventory-report'),
]
