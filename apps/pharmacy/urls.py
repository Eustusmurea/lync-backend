from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (DrugCategoryViewSet, DrugViewSet, DrugStockTransactionViewSet,
                    PrescriptionViewSet, DispenseViewSet)

router = DefaultRouter()
router.register('categories',    DrugCategoryViewSet,         basename='drug-category')
router.register('drugs',         DrugViewSet,                 basename='drug')
router.register('transactions',  DrugStockTransactionViewSet, basename='drug-transaction')
router.register('prescriptions', PrescriptionViewSet,         basename='prescription')
router.register('dispenses',     DispenseViewSet,             basename='dispense')

urlpatterns = [path('', include(router.urls))]
