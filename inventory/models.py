from django.conf import settings
from django.db import models


class StockMovement(models.Model):
    """
    Audit ledger tracking all inventory changes:
    - DISPATCH: Deducted when an order is confirmed
    - RETURN: Restored when a confirmed order is cancelled
    - IN: Manual increase by Admin
    - OUT: Manual decrease by Admin
    - OPENING: Initial stock set via CSV import or initialization
    """
    class MovementType(models.TextChoices):
        IN = 'IN', 'Manual Stock In'
        OUT = 'OUT', 'Manual Stock Out'
        DISPATCH = 'DISPATCH', 'Sales Order Dispatch'
        RETURN = 'RETURN', 'Sales Order Return/Cancellation'
        OPENING = 'OPENING', 'Opening Stock'

    product = models.ForeignKey(
        'masters.Product',
        on_delete=models.PROTECT,
        related_name='stock_movements',
        verbose_name="Product"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        verbose_name="Movement Type"
    )
    quantity_change = models.IntegerField(
        verbose_name="Quantity Change (+/-)"
    )
    related_order = models.ForeignKey(
        'sales.SalesOrder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name="Related Order"
    )
    reason = models.CharField(
        max_length=255,
        verbose_name="Reason"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='stock_movements',
        verbose_name="Created By"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['movement_type']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        sign = "+" if self.quantity_change > 0 else ""
        return f"{self.product.name}: {sign}{self.quantity_change} ({self.get_movement_type_display()})"
