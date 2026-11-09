from rest_framework import serializers
from .models import Product, Customer


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product master."""
    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'category', 'price', 'stock_quantity', 'status']


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer master."""
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'mobile', 'city', 'status']
