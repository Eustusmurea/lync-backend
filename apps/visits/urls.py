from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VisitViewSet, VitalsViewSet, DiagnosisViewSet, VisitBillingEventViewSet

router = DefaultRouter()
router.register('visits',   VisitViewSet,              basename='visit')
router.register('vitals',   VitalsViewSet,             basename='vitals')
router.register('diagnoses',DiagnosisViewSet,          basename='diagnosis')
router.register('charges',  VisitBillingEventViewSet,  basename='charge')

urlpatterns = [path('', include(router.urls))]
