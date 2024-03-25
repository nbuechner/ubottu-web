from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect

urlpatterns = [
    path("factoids/", include("factoids.urls")),
    path("admin/", admin.site.urls),
    path('', lambda request: redirect('factoids/', permanent=False)),  # Redirect from root to 'factoids'
]