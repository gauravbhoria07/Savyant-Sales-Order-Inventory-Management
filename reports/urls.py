from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('reports/customers/', views.customer_sales_summary, name='customer_sales_summary'),
    path('reports/products/', views.product_sales_summary, name='product_sales_summary'),
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
    path('reports/stock-movements/', views.stock_movement_report, name='stock_movement_report'),
]
