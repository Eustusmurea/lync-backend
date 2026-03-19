from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InsuranceProviderViewSet, InvoiceViewSet, InvoiceItemViewSet, PaymentViewSet

router = DefaultRouter()
router.register('insurance', InsuranceProviderViewSet, basename='insurance')
router.register('invoices',  InvoiceViewSet,           basename='invoice')
router.register('items',     InvoiceItemViewSet,       basename='invoice-item')
router.register('payments',  PaymentViewSet,           basename='payment')

urlpatterns = [path('', include(router.urls))]
