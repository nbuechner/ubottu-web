from django.urls import path
from . import views

urlpatterns = [
    #path('', views.list_facts, name='facts-list'),
    path('api/groups/members/<str:group_name>/', views.group_members, name='get_group_members'),
    path('api/people/<str:profile_id>/socials/matrix', views.matrix_profiles, name='get_matrix_accounts')
]
