from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from accounts.permissions import admin_required
from masters.models import Product
from .models import StockMovement
from .services import adjust_stock, InventoryError


@admin_required
def stock_adjustment(request):
    """
    Admin-only view to manually adjust inventory stock:
    - Increase (IN) or Decrease (OUT)
    - Validates mandatory reason and prevents negative stock.
    - Creates audit log in StockMovement.
    """
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        adjustment_type = request.POST.get('adjustment_type')
        quantity_str = request.POST.get('quantity')
        reason = request.POST.get('reason', '').strip()

        try:
            quantity = int(quantity_str)
            product, movement = adjust_stock(
                product_id=int(product_id),
                adjustment_type=adjustment_type,
                quantity=quantity,
                reason=reason,
                user=request.user,
            )
            messages.success(
                request,
                f"Stock for '{product.name}' adjusted by {movement.quantity_change:+d}. New stock: {product.stock_quantity}."
            )
            return redirect('inventory:stock_adjustment')
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid whole number for quantity.")
        except InventoryError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error adjusting stock: {str(e)}")

    products = Product.objects.all().order_by('name')
    recent_movements = StockMovement.objects.select_related('product', 'created_by').order_by('-timestamp')[:10]

    return render(request, 'inventory/stock_adjustment.html', {
        'products': products,
        'recent_movements': recent_movements,
    })


@login_required
def stock_movement_list(request):
    """
    Lists full stock movement audit ledger:
    - Filter by product, movement type, and date range.
    """
    product_id = request.GET.get('product', '').strip()
    movement_type = request.GET.get('type', '').strip()

    movements = StockMovement.objects.select_related('product', 'related_order', 'created_by').all()

    if product_id and product_id.isdigit():
        movements = movements.filter(product_id=int(product_id))

    if movement_type in [t[0] for t in StockMovement.MovementType.choices]:
        movements = movements.filter(movement_type=movement_type)

    paginator = Paginator(movements, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    products = Product.objects.all().order_by('name')

    return render(request, 'inventory/stock_movement_list.html', {
        'page_obj': page_obj,
        'products': products,
        'selected_product': product_id,
        'selected_type': movement_type,
        'movement_types': StockMovement.MovementType.choices,
    })
