from django.urls import path
from . import views

app_name = 'merchants'

urlpatterns = [
    path('search/', views.search_merchants, name='search'),
]
