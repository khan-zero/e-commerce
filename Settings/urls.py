#Settings/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
#from core.views import register_user # Import register_user

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include("dashboard.urls")),
    path('', include(('core.urls', 'core'))), # Register the 'core' namespace
    path('api/', include("api.urls")),
    path('marketing/', include('marketing.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
