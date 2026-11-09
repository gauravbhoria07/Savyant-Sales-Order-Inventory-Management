from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from sales.api import (
    ProductListAPIView,
    OrderListCreateAPIView,
    OrderDetailAPIView,
    OrderConfirmAPIView,
    OrderCancelAPIView,
)

def home_redirect(request):
    """Redirect root URL to dashboard or login."""
    if request.user.is_authenticated:
        return redirect('reports:dashboard')
    return redirect('login')

urlpatterns = [
    # Root redirect
    path('', home_redirect, name='home'),

    # Django admin
    path('admin/', admin.site.urls),

    # Authentication
    path('', include('accounts.urls')),

    # Business apps
    path('masters/', include('masters.urls')),
    path('sales/', include('sales.urls')),
    path('inventory/', include('inventory.urls')),
    path('', include('reports.urls')),

    # REST API endpoints (as specified in technical assignment)
    path('api/products/', ProductListAPIView.as_view(), name='api_products'),
    path('api/orders/', OrderListCreateAPIView.as_view(), name='api_orders_create'),
    path('api/orders/<int:pk>/', OrderDetailAPIView.as_view(), name='api_order_detail'),
    path('api/orders/<int:pk>/confirm/', OrderConfirmAPIView.as_view(), name='api_order_confirm'),
    path('api/orders/<int:pk>/cancel/', OrderCancelAPIView.as_view(), name='api_order_cancel'),
]
