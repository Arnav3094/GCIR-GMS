# proposals/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Define your app-specific routes here
    # Example: path('', views.index, name='index'),
    path('changelog/', views.weekly_changelog, name='weekly_changelog'),
]