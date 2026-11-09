from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, Value, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime

from accounts.permissions import admin_required
from masters.models import Customer, Product
from sales.models import SalesOrder, SalesOrderItem
from inventory.models import StockMovement


@login_required
def dashboard(request):
    """
    Main executive dashboard showing system overview metrics,
    recent orders, and quick action shortcuts.
    """
    total_customers = Customer.objects.filter(status=Customer.Status.ACTIVE).count()
    total_products = Product.objects.filter(status=Product.Status.ACTIVE).count()
    low_stock_count = Product.objects.filter(stock_quantity__lte=10, status=Product.Status.ACTIVE).count()

    if request.user.is_admin:
        confirmed_orders = SalesOrder.objects.filter(status=SalesOrder.Status.CONFIRMED)
        total_orders_count = SalesOrder.objects.count()
        recent_orders = SalesOrder.objects.select_related('customer', 'created_by').order_by('-created_at')[:5]
    else:
        confirmed_orders = SalesOrder.objects.filter(status=SalesOrder.Status.CONFIRMED, created_by=request.user)
        total_orders_count = SalesOrder.objects.filter(created_by=request.user).count()
        recent_orders = SalesOrder.objects.filter(created_by=request.user).select_related('customer').order_by('-created_at')[:5]

    total_revenue = confirmed_orders.aggregate(
        total=Coalesce(Sum('grand_total'), Value(Decimal('0.00'), output_field=DecimalField()))
    )['total']

    recent_movements = StockMovement.objects.select_related('product', 'created_by').order_by('-timestamp')[:5]

    context = {
        'total_customers': total_customers,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'total_revenue': total_revenue,
        'total_orders_count': total_orders_count,
        'recent_orders': recent_orders,
        'recent_movements': recent_movements,
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
def customer_sales_summary(request):
    """
    Customer Sales Summary Report:
    - Lists customer name, count of confirmed orders, and total net sales after discount.
    - Supports order date range filtering.
    - Includes customers with zero confirmed orders in the range.
    - Avoids counting one order multiple times when it contains multiple items.
    """
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()

    confirmed_filter = Q(orders__status=SalesOrder.Status.CONFIRMED)

    # Date range filters on order_date
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            confirmed_filter &= Q(orders__order_date__gte=start_date)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            confirmed_filter &= Q(orders__order_date__lte=end_date)
        except ValueError:
            pass

    customers = Customer.objects.annotate(
        confirmed_order_count=Count('orders', filter=confirmed_filter, distinct=True),
        total_sales=Coalesce(
            Sum('orders__grand_total', filter=confirmed_filter, distinct=True),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    ).order_by('-total_sales', 'name')

    total_sales_all = sum(c.total_sales for c in customers)
    total_orders_all = sum(c.confirmed_order_count for c in customers)

    return render(request, 'reports/customer_sales_summary.html', {
        'customers': customers,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'total_sales_all': total_sales_all,
        'total_orders_all': total_orders_all,
    })


@login_required
def product_sales_summary(request):
    """
    Product Sales Summary Report:
    - Product name
    - Quantity sold in Confirmed orders
    - Gross item value before order discount
    """
    confirmed_order_filter = Q(order_items__order__status=SalesOrder.Status.CONFIRMED)

    products = Product.objects.annotate(
        total_quantity_sold=Coalesce(
            Sum('order_items__quantity', filter=confirmed_order_filter),
            Value(0),
            output_field=IntegerField()
        ),
        gross_sales_value=Coalesce(
            Sum('order_items__amount', filter=confirmed_order_filter),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    ).order_by('-total_quantity_sold', 'name')

    total_qty_all = sum(p.total_quantity_sold for p in products)
    total_gross_all = sum(p.gross_sales_value for p in products)

    return render(request, 'reports/product_sales_summary.html', {
        'products': products,
        'total_qty_all': total_qty_all,
        'total_gross_all': total_gross_all,
    })


@login_required
def low_stock_report(request):
    """
    Low Stock Report:
    - Shows all products whose stock is less than or equal to a user-entered threshold (default 10).
    """
    threshold_str = request.GET.get('threshold', '10').strip()
    try:
        threshold = int(threshold_str)
        if threshold < 0:
            threshold = 10
    except ValueError:
        threshold = 10

    low_stock_products = Product.objects.filter(
        stock_quantity__lte=threshold
    ).order_by('stock_quantity', 'name')

    return render(request, 'reports/low_stock_report.html', {
        'products': low_stock_products,
        'threshold': threshold,
    })


@login_required
def stock_movement_report(request):
    """
    Stock Movement History Report:
    - Lists chronological stock movements with product, movement type, quantity change,
      order reference, reason, and timestamp.
    """
    product_id = request.GET.get('product', '').strip()
    movement_type = request.GET.get('type', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    movements = StockMovement.objects.select_related('product', 'related_order', 'created_by').all()

    if product_id and product_id.isdigit():
        movements = movements.filter(product_id=int(product_id))

    if movement_type:
        movements = movements.filter(movement_type=movement_type)

    if start_date:
        movements = movements.filter(timestamp__date__gte=start_date)

    if end_date:
        movements = movements.filter(timestamp__date__lte=end_date)

    products = Product.objects.all().order_by('name')

    return render(request, 'reports/stock_movement_report.html', {
        'movements': movements,
        'products': products,
        'product_id': product_id,
        'movement_type': movement_type,
        'start_date': start_date,
        'end_date': end_date,
        'movement_types': StockMovement.MovementType.choices,
    })
