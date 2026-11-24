from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestPanelViewSet, TestParameterViewSet, TestOrderViewSet, TestResultViewSet

router = DefaultRouter()
router.register('panels', TestPanelViewSet, basename='panel')
router.register('parameters', TestParameterViewSet, basename='parameter')
router.register('orders', TestOrderViewSet, basename='order')
router.register('results', TestResultViewSet, basename='result')

urlpatterns = [path('', include(router.urls))]
