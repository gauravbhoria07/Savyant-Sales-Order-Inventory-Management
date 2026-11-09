from django.db import transaction
from masters.models import Product
from sales.models import SalesOrder
from .models import StockMovement


class InventoryError(Exception):
    """Custom exception for inventory and order transition validation errors."""
    pass


def confirm_sales_order(order_id: int, user) -> SalesOrder:
    """
    Confirms a Sales Order and deducts inventory stock:
    1. Locks the order with select_for_update() to prevent race conditions.
    2. Validates that the order is currently in DRAFT status.
    3. Locks all involved product rows in consistent order to prevent deadlocks.
    4. Checks stock availability for all products.
    5. If any product is insufficient, rolls back the entire transaction.
    6. If all products are available, deducts stock and logs StockMovement records.
    7. Updates order status to CONFIRMED.
    """
    with transaction.atomic():
        try:
            order = SalesOrder.objects.select_for_update().get(id=order_id)
        except SalesOrder.DoesNotExist:
            raise InventoryError("Sales order not found.")

        # Prevent duplicate confirmation
        if order.status != SalesOrder.Status.DRAFT:
            raise InventoryError(
                f"Cannot confirm order {order.order_number} because it is already {order.get_status_display()}."
            )

        items = list(order.items.select_related('product').all())
        if not items:
            raise InventoryError("Cannot confirm an order with no items.")

        # Sort product IDs to lock products in deterministic order (prevents deadlocks)
        product_ids = sorted([item.product_id for item in items])
        locked_products = {
            p.id: p
            for p in Product.objects.select_for_update().filter(id__in=product_ids)
        }

        # Step 1: Check stock sufficiency for EVERY item
        insufficient_details = []
        for item in items:
            prod = locked_products.get(item.product_id)
            if not prod or prod.stock_quantity < item.quantity:
                available = prod.stock_quantity if prod else 0
                insufficient_details.append(
                    f"{prod.name if prod else 'Item'} (Available: {available}, Required: {item.quantity})"
                )

        if insufficient_details:
            # Transaction rolls back automatically when exception is raised
            raise InventoryError(
                f"Insufficient stock for: {', '.join(insufficient_details)}. No changes were made."
            )

        # Step 2: All items are sufficient - deduct stock and record movement
        for item in items:
            prod = locked_products[item.product_id]
            prod.stock_quantity -= item.quantity
            prod.save(update_fields=['stock_quantity', 'updated_at'])

            StockMovement.objects.create(
                product=prod,
                movement_type=StockMovement.MovementType.DISPATCH,
                quantity_change=-item.quantity,
                related_order=order,
                reason=f"Order {order.order_number} confirmed and dispatched",
                created_by=user,
            )

        # Step 3: Transition status to Confirmed
        order.status = SalesOrder.Status.CONFIRMED
        order.save(update_fields=['status', 'updated_at'])
        return order


def cancel_sales_order(order_id: int, user) -> SalesOrder:
    """
    Cancels a Sales Order:
    - If previously CONFIRMED: restores deducted stock and logs StockMovement records.
    - If DRAFT: cancels without stock change (draft never deducted stock).
    - If already CANCELLED: rejects duplicate cancellation request.
    All inside a single atomic transaction.
    """
    with transaction.atomic():
        try:
            order = SalesOrder.objects.select_for_update().get(id=order_id)
        except SalesOrder.DoesNotExist:
            raise InventoryError("Sales order not found.")

        if order.status == SalesOrder.Status.CANCELLED:
            raise InventoryError(f"Order {order.order_number} is already cancelled.")

        previous_status = order.status

        # If order was confirmed, restore stock
        if previous_status == SalesOrder.Status.CONFIRMED:
            items = list(order.items.select_related('product').all())
            product_ids = sorted([item.product_id for item in items])
            locked_products = {
                p.id: p
                for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }

            for item in items:
                prod = locked_products[item.product_id]
                prod.stock_quantity += item.quantity
                prod.save(update_fields=['stock_quantity', 'updated_at'])

                StockMovement.objects.create(
                    product=prod,
                    movement_type=StockMovement.MovementType.RETURN,
                    quantity_change=item.quantity,
                    related_order=order,
                    reason=f"Order {order.order_number} cancelled; stock returned to inventory",
                    created_by=user,
                )

        order.status = SalesOrder.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        return order


def adjust_stock(product_id: int, adjustment_type: str, quantity: int, reason: str, user):
    """
    Performs a manual stock adjustment by Admin:
    - adjustment_type: 'IN' (increase) or 'OUT' (decrease)
    - quantity: positive integer
    - reason: non-empty string explaining the adjustment
    - user: Admin user performing the adjustment
    """
    if not reason or not reason.strip():
        raise InventoryError("A mandatory reason must be provided for manual stock adjustment.")

    if not isinstance(quantity, int) or quantity <= 0:
        raise InventoryError("Adjustment quantity must be a positive whole number.")

    with transaction.atomic():
        try:
            product = Product.objects.select_for_update().get(id=product_id)
        except Product.DoesNotExist:
            raise InventoryError("Product not found.")

        if adjustment_type == 'IN':
            product.stock_quantity += quantity
            qty_change = quantity
            movement_type = StockMovement.MovementType.IN
        elif adjustment_type == 'OUT':
            if product.stock_quantity < quantity:
                raise InventoryError(
                    f"Cannot reduce stock by {quantity}. Current available stock is only {product.stock_quantity}."
                )
            product.stock_quantity -= quantity
            qty_change = -quantity
            movement_type = StockMovement.MovementType.OUT
        else:
            raise InventoryError("Invalid adjustment type. Must be 'IN' or 'OUT'.")

        product.save(update_fields=['stock_quantity', 'updated_at'])

        movement = StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity_change=qty_change,
            reason=reason.strip(),
            created_by=user,
        )
        return product, movement
