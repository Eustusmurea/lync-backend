from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT Auth
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # App routes
    path('api/users/', include('apps.users.urls')),
    path('api/samples/', include('apps.samples.urls')),
    path('api/tests/', include('apps.tests.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/billing/', include('apps.billing.urls')),
    path('api/pharmacy/', include('apps.pharmacy.urls')),
    path('api/visits/', include('apps.visits.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
