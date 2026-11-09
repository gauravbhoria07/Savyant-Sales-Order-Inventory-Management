import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


def generate_order_number():
    """
    Generates a human-friendly unique order number like SO-YYYYMMDD-XXXX.
    Example: SO-20261109-A1B2
    """
    date_str = timezone.now().strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"SO-{date_str}-{unique_suffix}"


class SalesOrder(models.Model):
    """
    Sales Order entity representing a customer's purchase order.
    Enforces strict status transitions and server-side calculated totals.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    order_number = models.CharField(
        max_length=32,
        unique=True,
        default=generate_order_number,
        editable=False,
        verbose_name="Order Number"
    )
    customer = models.ForeignKey(
        'masters.Customer',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Customer"
    )
    order_date = models.DateField(default=timezone.now, verbose_name="Order Date")
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Order Status"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('20.00'))
        ],
        verbose_name="Discount %"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Subtotal"
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Discount Amount"
    )
    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Grand Total"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sales_orders',
        verbose_name="Created By"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['order_date']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.customer.name} ({self.get_status_display()})"

    @property
    def is_draft(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def is_confirmed(self) -> bool:
        return self.status == self.Status.CONFIRMED

    @property
    def is_cancelled(self) -> bool:
        return self.status == self.Status.CANCELLED

    @property
    def is_read_only(self) -> bool:
        """Confirmed and Cancelled orders are strictly read-only."""
        return self.status in (self.Status.CONFIRMED, self.Status.CANCELLED)

    def calculate_totals(self, save: bool = False):
        """
        Recalculates all order totals based on current items:
        - Subtotal = Sum of (quantity * rate) of all items
        - Discount Amount = Subtotal * (Discount % / 100)
        - Grand Total = Subtotal - Discount Amount
        Consistent rounding to 2 decimal places using Decimal ROUND_HALF_UP.
        """
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.amount

        self.subtotal = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        disc_rate = (self.discount_percentage or Decimal('0.00')) / Decimal('100.00')
        self.discount_amount = (self.subtotal * disc_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.grand_total = (self.subtotal - self.discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if save:
            self.save(update_fields=['subtotal', 'discount_amount', 'grand_total', 'updated_at'])


class SalesOrderItem(models.Model):
    """
    Sales Order Item representing individual product rows in an order.
    Enforces positive quantity, snapshots rate, and prevents duplicate products in the same order.
    """
    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Sales Order"
    )
    product = models.ForeignKey(
        'masters.Product',
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name="Product"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Quantity"
    )
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Rate Snapshot"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Item Amount"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product'],
                name='unique_product_per_order'
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='order_item_qty_positive'
            ),
        ]

    def save(self, *args, **kwargs):
        """
        Calculates item amount = quantity * rate before saving.
        """
        qty = Decimal(str(self.quantity))
        rate_val = Decimal(str(self.rate))
        self.amount = (qty * rate_val).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} (Qty: {self.quantity}) - {self.order.order_number}"
