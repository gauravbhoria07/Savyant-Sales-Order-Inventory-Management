from django import forms
from .models import Customer, Product


class CustomerForm(forms.ModelForm):
    """
    Form for creating and editing customer master records.
    """
    class Meta:
        model = Customer
        fields = ['name', 'email', 'mobile', 'city', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit mobile number'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class ProductForm(forms.ModelForm):
    """
    Form for creating and editing product master records.
    """
    class Meta:
        model = Product
        fields = ['code', 'name', 'category', 'price', 'stock_quantity', 'status']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PRD-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Product price cannot be negative.")
        return price

    def clean_stock_quantity(self):
        stock = self.cleaned_data.get('stock_quantity')
        if stock is not None and stock < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return stock
