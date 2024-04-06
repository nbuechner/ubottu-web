from django.urls import path
from . import views

urlpatterns = [
    #path('', views.list_facts, name='facts-list'),
    path('api/bugtracker/launchpad/<int:bug_id>/', views.get_launchpad_bug, name='get_launchpad_bug'),
    path('api/bugtracker/github/<str:owner>/<str:repo>/<int:bug_id>/', views.get_github_bug, name='get_github_bug'),
]
