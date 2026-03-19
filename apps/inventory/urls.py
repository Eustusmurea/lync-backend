from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReagentViewSet, StockTransactionViewSet

router = DefaultRouter()
router.register('reagents', ReagentViewSet, basename='reagent')
router.register('transactions', StockTransactionViewSet, basename='transaction')

urlpatterns = [path('', include(router.urls))]
