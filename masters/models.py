from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Customer(models.Model):
    """
    Customer entity for storing client master records.
    Referenced by SalesOrder with on_delete=models.PROTECT to prevent accidental deletion.
    """
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    name = models.CharField(max_length=150, verbose_name="Customer Name")
    email = models.EmailField(blank=True, verbose_name="Email Address")
    mobile = models.CharField(max_length=15, verbose_name="Mobile Number")
    city = models.CharField(max_length=100, verbose_name="City")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['mobile']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE


class Product(models.Model):
    """
    Product entity representing inventory items.
    Enforces unique code and non-negative constraints on price and stock quantity.
    """
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'

    code = models.CharField(max_length=30, unique=True, verbose_name="Product Code")
    name = models.CharField(max_length=150, verbose_name="Product Name")
    category = models.CharField(max_length=100, verbose_name="Category")
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Unit Price"
    )
    stock_quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Available Stock"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='product_price_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0),
                name='product_stock_non_negative'
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE
