from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from lyncare.auth_views import LoginView, LogoutView, RefreshView


def health(_request):
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            db_ok = True
    except Exception:
        db_ok = False
    payload = {'status': 'ok' if db_ok else 'degraded', 'db': db_ok}
    return JsonResponse(payload, status=200 if db_ok else 503)


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('api/auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='token_logout'),
    path('api/users/', include('apps.users.urls')),
    path('api/samples/', include('apps.samples.urls')),
    path('api/tests/', include('apps.tests.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/billing/', include('apps.billing.urls')),
    path('api/pharmacy/', include('apps.pharmacy.urls')),
    path('api/visits/', include('apps.visits.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
