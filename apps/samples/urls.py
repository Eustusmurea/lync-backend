from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .serializers import PatientViewSet, SampleViewSet

router = DefaultRouter()
router.register('patients', PatientViewSet, basename='patient')
router.register('', SampleViewSet, basename='sample')

urlpatterns = [path('', include(router.urls))]
