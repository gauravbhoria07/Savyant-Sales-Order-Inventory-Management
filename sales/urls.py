from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('create/', views.order_create, name='order_create'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/confirm/', views.order_confirm, name='order_confirm'),
    path('<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
]
