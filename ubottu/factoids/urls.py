from django.urls import path
from .views import FactList
from . import views

urlpatterns = [
    path('', views.list_facts, name='facts-list'),
    path('api/citytime/<str:city_name>/', views.city_time, name='citytime'),
    path('api/facts/', FactList.as_view(), name='fact-list'),  # For listing all facts
    path('api/facts/<int:id>/', FactList.as_view(), name='fact-detail-by-id'),  # For fetching by id
    path('api/facts/<slug:name>/', FactList.as_view(), name='fact-detail-by-name'),  # For fetching by name
]
