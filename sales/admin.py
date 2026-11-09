from django.contrib import admin
from .models import SalesOrder, SalesOrderItem


class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 0
    readonly_fields = ('amount',)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'order_date', 'status', 'grand_total', 'created_by')
    list_filter = ('status', 'order_date')
    search_fields = ('order_number', 'customer__name')
    inlines = [SalesOrderItemInline]
    readonly_fields = ('order_number', 'subtotal', 'discount_amount', 'grand_total', 'created_at', 'updated_at')
