# credit_approval_system/urls.py
from django.contrib import admin
from django.urls import path, include # Import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')), # Include your app's URLs under '/api/' prefix
]