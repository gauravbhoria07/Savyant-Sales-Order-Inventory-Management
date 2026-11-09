from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ValidationError
from masters.models import Customer, Product
from .models import SalesOrder, SalesOrderItem


class OrderValidationError(Exception):
    """Custom exception for sales order validation errors."""
    pass


def create_sales_order(customer_id: int, items_data: list, discount_percentage: Decimal, user) -> SalesOrder:
    """
    Validates and creates a new Draft Sales Order:
    - customer_id: ID of an ACTIVE customer.
    - items_data: list of dicts [{'product_id': int, 'quantity': int}]
    - discount_percentage: Decimal between 0 and 20.
    - user: authenticated user creating the order.
    All financial values are calculated strictly on the backend.
    """
    if discount_percentage is None:
        discount_percentage = Decimal('0.00')
    else:
        discount_percentage = Decimal(str(discount_percentage))

    if discount_percentage < Decimal('0.00') or discount_percentage > Decimal('20.00'):
        raise OrderValidationError("Discount percentage must be between 0% and 20%.")

    # Validate active customer
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        raise OrderValidationError("Selected customer does not exist.")

    if customer.status != Customer.Status.ACTIVE:
        raise OrderValidationError("Orders can only be created for ACTIVE customers.")

    # Validate items
    if not items_data or len(items_data) == 0:
        raise OrderValidationError("An order must contain at least one item.")

    seen_products = set()
    cleaned_items = []

    for idx, item in enumerate(items_data, start=1):
        product_id = item.get('product_id')
        quantity = item.get('quantity')

        if not product_id:
            raise OrderValidationError(f"Row {idx}: Product selection is required.")

        if product_id in seen_products:
            raise OrderValidationError(f"Row {idx}: Duplicate product selected. Each product can only appear once per order.")
        seen_products.add(product_id)

        try:
            qty_int = int(quantity)
        except (ValueError, TypeError):
            raise OrderValidationError(f"Row {idx}: Quantity must be a valid integer.")

        if qty_int <= 0:
            raise OrderValidationError(f"Row {idx}: Quantity must be a positive whole number (greater than 0).")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise OrderValidationError(f"Row {idx}: Product does not exist.")

        if product.status != Product.Status.ACTIVE:
            raise OrderValidationError(f"Row {idx}: Product '{product.name}' is inactive and cannot be ordered.")

        cleaned_items.append({
            'product': product,
            'quantity': qty_int,
            'rate': product.price, # Snapshot current product price from database
        })

    # Atomic creation of order and order items
    with transaction.atomic():
        order = SalesOrder.objects.create(
            customer=customer,
            status=SalesOrder.Status.DRAFT,
            discount_percentage=discount_percentage,
            created_by=user,
        )

        subtotal = Decimal('0.00')
        for clean_item in cleaned_items:
            qty = clean_item['quantity']
            rate = clean_item['rate']
            amt = (Decimal(str(qty)) * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            subtotal += amt

            SalesOrderItem.objects.create(
                order=order,
                product=clean_item['product'],
                quantity=qty,
                rate=rate,
                amount=amt,
            )

        # Calculate backend discount and grand total
        disc_factor = discount_percentage / Decimal('100.00')
        discount_amount = (subtotal * disc_factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        grand_total = (subtotal - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        order.subtotal = subtotal
        order.discount_amount = discount_amount
        order.grand_total = grand_total
        order.save(update_fields=['subtotal', 'discount_amount', 'grand_total'])

        return order
