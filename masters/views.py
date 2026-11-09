from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from accounts.permissions import admin_required
from .forms import CustomerForm, ProductForm
from .models import Customer, Product
from .csv_import import import_products_csv


# -------------------------------------------------------------
# Customer Views
# -------------------------------------------------------------

@login_required
def customer_list(request):
    """
    Lists customers with search by name, email, mobile and status filter.
    Sales Users can only see Active customers.
    Admin users can see all and manage them.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    customers = Customer.objects.all()

    # Sales users only see Active customers
    if not request.user.is_admin:
        customers = customers.filter(status=Customer.Status.ACTIVE)
    elif status_filter in [Customer.Status.ACTIVE, Customer.Status.INACTIVE]:
        customers = customers.filter(status=status_filter)

    # Search filter
    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(mobile__icontains=query)
        )

    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'masters/customer_list.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
    })


@admin_required
def customer_create(request):
    """Admin-only view to create a new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f"Customer '{customer.name}' created successfully.")
            return redirect('masters:customer_list')
    else:
        form = CustomerForm()

    return render(request, 'masters/customer_form.html', {
        'form': form,
        'title': 'Add New Customer',
    })


@admin_required
def customer_edit(request, pk):
    """Admin-only view to edit customer details."""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer '{customer.name}' updated successfully.")
            return redirect('masters:customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'masters/customer_form.html', {
        'form': form,
        'customer': customer,
        'title': f'Edit Customer: {customer.name}',
    })


@admin_required
def customer_delete(request, pk):
    """
    Admin-only view to safely delete a customer.
    Prevents deletion if referenced by existing sales orders.
    """
    customer = get_object_or_404(Customer, pk=pk)

    if customer.orders.exists():
        messages.error(
            request,
            f"Cannot delete customer '{customer.name}' because they are referenced by {customer.orders.count()} sales order(s). "
            "Please deactivate the customer instead."
        )
        return redirect('masters:customer_list')

    if request.method == 'POST':
        customer_name = customer.name
        customer.delete()
        messages.success(request, f"Customer '{customer_name}' was safely deleted.")
        return redirect('masters:customer_list')

    return render(request, 'masters/customer_confirm_delete.html', {
        'customer': customer,
    })


# -------------------------------------------------------------
# Product Views
# -------------------------------------------------------------

@login_required
def product_list(request):
    """
    Lists products with search by code or name, and category/status filter.
    Sales Users can only see Active products.
    """
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    status_filter = request.GET.get('status', '').strip()

    products = Product.objects.all()

    # Sales users only see Active products
    if not request.user.is_admin:
        products = products.filter(status=Product.Status.ACTIVE)
    elif status_filter in [Product.Status.ACTIVE, Product.Status.INACTIVE]:
        products = products.filter(status=status_filter)

    if category_filter:
        products = products.filter(category__iexact=category_filter)

    if query:
        products = products.filter(
            Q(code__icontains=query) |
            Q(name__icontains=query)
        )

    categories = Product.objects.values_list('category', flat=True).distinct().order_by('category')

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'masters/product_list.html', {
        'page_obj': page_obj,
        'query': query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'categories': categories,
    })


@admin_required
def product_create(request):
    """Admin-only view to create a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect('masters:product_list')
    else:
        form = ProductForm()

    return render(request, 'masters/product_form.html', {
        'form': form,
        'title': 'Add New Product',
    })


@admin_required
def product_edit(request, pk):
    """Admin-only view to edit product details."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('masters:product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'masters/product_form.html', {
        'form': form,
        'product': product,
        'title': f'Edit Product: {product.name}',
    })


@admin_required
def product_delete(request, pk):
    """
    Admin-only view to safely delete a product.
    Prevents deletion if referenced by order items or stock movements.
    """
    product = get_object_or_404(Product, pk=pk)

    has_orders = product.order_items.exists()
    has_movements = product.stock_movements.exists()

    if has_orders or has_movements:
        reasons = []
        if has_orders:
            reasons.append(f"{product.order_items.count()} order item(s)")
        if has_movements:
            reasons.append(f"{product.stock_movements.count()} stock movement ledger entry(ies)")
        messages.error(
            request,
            f"Cannot delete product '{product.name}' because it has {', and '.join(reasons)}. "
            "Please deactivate the product instead."
        )
        return redirect('masters:product_list')

    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f"Product '{product_name}' was safely deleted.")
        return redirect('masters:product_list')

    return render(request, 'masters/product_confirm_delete.html', {
        'product': product,
    })


@admin_required
def product_import_csv(request):
    """
    Admin-only view to upload and import products via CSV.
    Enforces all-or-nothing validation and reports row-numbered errors.
    """
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        success, errors, count = import_products_csv(csv_file, request.user)

        if success:
            messages.success(request, f"Successfully imported {count} product(s) with opening stock movements!")
            return redirect('masters:product_list')
        else:
            return render(request, 'masters/product_csv_import.html', {
                'errors': errors,
            })

    return render(request, 'masters/product_csv_import.html')
