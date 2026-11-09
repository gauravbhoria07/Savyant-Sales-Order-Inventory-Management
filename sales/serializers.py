from decimal import Decimal
from rest_framework import serializers
from .models import SalesOrder, SalesOrderItem
from masters.serializers import ProductSerializer, CustomerSerializer


class SalesOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for individual items in an order."""
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ['id', 'product', 'product_code', 'product_name', 'quantity', 'rate', 'amount']


class SalesOrderReadSerializer(serializers.ModelSerializer):
    """Detailed serializer for retrieving an order."""
    customer = CustomerSerializer(read_only=True)
    items = SalesOrderItemSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            'id',
            'order_number',
            'customer',
            'order_date',
            'status',
            'discount_percentage',
            'subtotal',
            'discount_amount',
            'grand_total',
            'created_by_username',
            'created_at',
            'items',
        ]


class OrderItemInputSerializer(serializers.Serializer):
    """Input serializer for a single item when creating an order."""
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)


class OrderCreateInputSerializer(serializers.Serializer):
    """Input serializer for order creation."""
    customer_id = serializers.IntegerField(required=True)
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal('0.00'),
        min_value=Decimal('0.00'),
        max_value=Decimal('20.00')
    )
    items = OrderItemInputSerializer(many=True, required=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("An order must contain at least one item.")
        
        seen_products = set()
        for item in value:
            pid = item.get('product_id')
            if pid in seen_products:
                raise serializers.ValidationError(f"Duplicate product_id {pid} provided in items list.")
            seen_products.add(pid)
        return value
