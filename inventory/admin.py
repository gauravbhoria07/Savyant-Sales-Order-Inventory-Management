from django.contrib import admin
from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity_change', 'related_order', 'reason', 'created_by', 'timestamp')
    list_filter = ('movement_type', 'timestamp')
    search_fields = ('product__name', 'product__code', 'reason', 'related_order__order_number')
    readonly_fields = ('timestamp',)
