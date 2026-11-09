import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from masters.models import Customer, Product
from inventory.services import confirm_sales_order, cancel_sales_order, InventoryError
from .models import SalesOrder, SalesOrderItem
from .services import create_sales_order, OrderValidationError


@login_required
def order_list(request):
    """
    Lists sales orders with filtering by status, customer, and search.
    Enforces security:
    - Admin users can view all sales orders.
    - Sales users can ONLY view their own orders.
    """
    status_filter = request.GET.get('status', '').strip()
    customer_id = request.GET.get('customer', '').strip()
    query = request.GET.get('q', '').strip()

    # Base queryset according to user role
    if request.user.is_admin:
        orders = SalesOrder.objects.select_related('customer', 'created_by').all()
    else:
        orders = SalesOrder.objects.filter(created_by=request.user).select_related('customer', 'created_by')

    # Apply filters
    if status_filter in [SalesOrder.Status.DRAFT, SalesOrder.Status.CONFIRMED, SalesOrder.Status.CANCELLED]:
        orders = orders.filter(status=status_filter)

    if customer_id and customer_id.isdigit():
        orders = orders.filter(customer_id=int(customer_id))

    if query:
        orders = orders.filter(
            Q(order_number__icontains=query) |
            Q(customer__name__icontains=query)
        )

    customers = Customer.objects.filter(status=Customer.Status.ACTIVE).order_by('name')

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'sales/order_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'customer_id': customer_id,
        'query': query,
        'customers': customers,
    })


@login_required
def order_create(request):
    """
    Create a new Sales Order with dynamic multiple product rows:
    - Provides active customers and active products to template.
    - Handles POST request with validated items and backend calculation.
    """
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        discount_percentage = request.POST.get('discount_percentage', '0.00')

        # Extract dynamic item rows from POST
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')

        items_data = []
        for p_id, q_val in zip(product_ids, quantities):
            if p_id and q_val:
                items_data.append({
                    'product_id': p_id,
                    'quantity': q_val,
                })

        try:
            order = create_sales_order(
                customer_id=customer_id,
                items_data=items_data,
                discount_percentage=discount_percentage,
                user=request.user,
            )
            messages.success(request, f"Sales Order '{order.order_number}' created successfully as Draft.")
            return redirect('sales:order_detail', pk=order.pk)
        except OrderValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")

    # Active customers and active products only
    active_customers = Customer.objects.filter(status=Customer.Status.ACTIVE).order_by('name')
    active_products = Product.objects.filter(status=Product.Status.ACTIVE).order_by('name')

    # Prepare JSON serializable product dictionary for fast client-side JS lookup
    products_catalog = [
        {
            'id': p.id,
            'code': p.code,
            'name': p.name,
            'price': float(p.price),
            'stock': p.stock_quantity,
        }
        for p in active_products
    ]

    return render(request, 'sales/order_form.html', {
        'customers': active_customers,
        'products': active_products,
        'products_catalog_json': json.dumps(products_catalog),
    })


@login_required
def order_detail(request, pk):
    """
    Detailed view of a sales order.
    Security: Sales User CANNOT access orders created by another user.
    """
    order = get_object_or_404(
        SalesOrder.objects.select_related('customer', 'created_by'),
        pk=pk
    )

    # Backend permission check: sales user cannot access other users' orders
    if not request.user.is_admin and order.created_by != request.user:
        raise PermissionDenied("You do not have permission to view or modify this order.")

    items = order.items.select_related('product').all()

    return render(request, 'sales/order_detail.html', {
        'order': order,
        'items': items,
    })


@login_required
@require_POST
def order_confirm(request, pk):
    """
    Confirms an order and deducts inventory stock:
    - Enforces user permission.
    - Atomic transaction & concurrency lock.
    """
    order = get_object_or_404(SalesOrder, pk=pk)

    if not request.user.is_admin and order.created_by != request.user:
        raise PermissionDenied("You do not have permission to confirm this order.")

    try:
        confirm_sales_order(order.id, request.user)
        messages.success(request, f"Order {order.order_number} confirmed successfully. Inventory has been updated.")
    except InventoryError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error confirming order: {str(e)}")

    return redirect('sales:order_detail', pk=pk)


@login_required
@require_POST
def order_cancel(request, pk):
    """
    Cancels an order and restores stock if it was previously confirmed.
    """
    order = get_object_or_404(SalesOrder, pk=pk)

    if not request.user.is_admin and order.created_by != request.user:
        raise PermissionDenied("You do not have permission to cancel this order.")

    try:
        cancel_sales_order(order.id, request.user)
        messages.warning(request, f"Order {order.order_number} has been cancelled.")
    except InventoryError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error cancelling order: {str(e)}")

    return redirect('sales:order_detail', pk=pk)
