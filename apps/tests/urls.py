from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestPanelViewSet, TestOrderViewSet, TestResultViewSet

router = DefaultRouter()
router.register('panels', TestPanelViewSet, basename='panel')
router.register('orders', TestOrderViewSet, basename='order')
router.register('results', TestResultViewSet, basename='result')

urlpatterns = [path('', include(router.urls))]
