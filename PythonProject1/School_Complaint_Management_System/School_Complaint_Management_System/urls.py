from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('SCMS.urls')),
]

if settings.DEBUG:
    if settings.STATIC_URL and not settings.STATIC_URL.startswith(('http://', 'https://')):
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    if settings.MEDIA_URL and not settings.MEDIA_URL.startswith(('http://', 'https://')):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)