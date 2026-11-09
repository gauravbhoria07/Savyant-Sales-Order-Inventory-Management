from django.contrib import admin
from .models import Customer, Product


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'email', 'city', 'status', 'created_at')
    list_filter = ('status', 'city')
    search_fields = ('name', 'mobile', 'email', 'city')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'price', 'stock_quantity', 'status')
    list_filter = ('category', 'status')
    search_fields = ('code', 'name', 'category')
