from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('adjust/', views.stock_adjustment, name='stock_adjustment'),
    path('movements/', views.stock_movement_list, name='stock_movements'),
]
