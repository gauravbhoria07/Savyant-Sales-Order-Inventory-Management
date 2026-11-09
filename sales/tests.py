from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from masters.models import Customer, Product
from sales.models import SalesOrder, SalesOrderItem
from sales.services import create_sales_order, OrderValidationError

User = get_user_model()


class SalesOrderTestCase(TestCase):
    """
    Automated test suite for Sales Order calculations, permissions, and validations.
    """

    def setUp(self):
        # Create Users
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='Password@123',
            role=User.Role.ADMIN
        )
        self.sales_user_1 = User.objects.create_user(
            username='sales1_test',
            email='sales1@test.com',
            password='Password@123',
            role=User.Role.SALES_USER
        )
        self.sales_user_2 = User.objects.create_user(
            username='sales2_test',
            email='sales2@test.com',
            password='Password@123',
            role=User.Role.SALES_USER
        )

        # Create Active Customer
        self.customer = Customer.objects.create(
            name='Acme Enterprises',
            email='contact@acme.com',
            mobile='9876543210',
            city='Bangalore',
            status=Customer.Status.ACTIVE
        )

        # Create Inactive Customer
        self.inactive_customer = Customer.objects.create(
            name='Defunct Traders',
            mobile='9123456789',
            city='Pune',
            status=Customer.Status.INACTIVE
        )

        # Create Products
        self.keyboard = Product.objects.create(
            code='PRD-KB',
            name='Keyboard',
            category='Accessories',
            price=Decimal('1500.00'),
            stock_quantity=20,
            status=Product.Status.ACTIVE
        )
        self.mouse = Product.objects.create(
            code='PRD-MS',
            name='Mouse',
            category='Accessories',
            price=Decimal('500.00'),
            stock_quantity=50,
            status=Product.Status.ACTIVE
        )

    def test_multi_item_order_calculations_and_discount(self):
        """
        Tests the exact assignment scenario:
        Keyboard (qty 2 * 1500 = 3000) + Mouse (qty 3 * 500 = 1500)
        Subtotal = 4500.00
        Discount 10% = 450.00
        Grand Total = 4050.00
        """
        items_data = [
            {'product_id': self.keyboard.id, 'quantity': 2},
            {'product_id': self.mouse.id, 'quantity': 3},
        ]
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=items_data,
            discount_percentage=Decimal('10.00'),
            user=self.sales_user_1
        )

        self.assertEqual(order.subtotal, Decimal('4500.00'))
        self.assertEqual(order.discount_percentage, Decimal('10.00'))
        self.assertEqual(order.discount_amount, Decimal('450.00'))
        self.assertEqual(order.grand_total, Decimal('4050.00'))
        self.assertEqual(order.items.count(), 2)

    def test_zero_quantity_rejected(self):
        """Order item with quantity 0 must be rejected."""
        items_data = [{'product_id': self.keyboard.id, 'quantity': 0}]
        with self.assertRaises(OrderValidationError):
            create_sales_order(
                customer_id=self.customer.id,
                items_data=items_data,
                discount_percentage=Decimal('0.00'),
                user=self.sales_user_1
            )

    def test_negative_quantity_rejected(self):
        """Order item with negative quantity must be rejected."""
        items_data = [{'product_id': self.keyboard.id, 'quantity': -5}]
        with self.assertRaises(OrderValidationError):
            create_sales_order(
                customer_id=self.customer.id,
                items_data=items_data,
                discount_percentage=Decimal('0.00'),
                user=self.sales_user_1
            )

    def test_discount_outside_0_to_20_percent_rejected(self):
        """Discounts below 0% or above 20% must be rejected."""
        items_data = [{'product_id': self.keyboard.id, 'quantity': 1}]

        # Over 20%
        with self.assertRaises(OrderValidationError):
            create_sales_order(
                customer_id=self.customer.id,
                items_data=items_data,
                discount_percentage=Decimal('25.00'),
                user=self.sales_user_1
            )

        # Negative discount
        with self.assertRaises(OrderValidationError):
            create_sales_order(
                customer_id=self.customer.id,
                items_data=items_data,
                discount_percentage=Decimal('-5.00'),
                user=self.sales_user_1
            )

    def test_duplicate_products_in_same_order_rejected(self):
        """Duplicate products within the same order must be rejected."""
        items_data = [
            {'product_id': self.keyboard.id, 'quantity': 1},
            {'product_id': self.keyboard.id, 'quantity': 2},
        ]
        with self.assertRaises(OrderValidationError):
            create_sales_order(
                customer_id=self.customer.id,
                items_data=items_data,
                discount_percentage=Decimal('0.00'),
                user=self.sales_user_1
            )

    def test_order_creation_with_inactive_customer_rejected(self):
        """Orders cannot be placed for inactive customers."""
        items_data = [{'product_id': self.keyboard.id, 'quantity': 1}]
        with self.assertRaises(OrderValidationError):
            create_sales_order(
                customer_id=self.inactive_customer.id,
                items_data=items_data,
                discount_percentage=Decimal('0.00'),
                user=self.sales_user_1
            )

    def test_sales_user_denied_access_to_other_users_order_view(self):
        """Sales User cannot access another user's order in web UI."""
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=[{'product_id': self.keyboard.id, 'quantity': 1}],
            discount_percentage=Decimal('0.00'),
            user=self.sales_user_1
        )

        client = Client()
        client.login(username='sales2_test', password='Password@123')

        # Accessing sales1's order as sales2 must yield 403 Forbidden
        response = client.get(reverse('sales:order_detail', kwargs={'pk': order.id}))
        self.assertEqual(response.status_code, 403)

    def test_sales_user_denied_access_to_other_users_order_api(self):
        """Sales User cannot access another user's order via REST API."""
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=[{'product_id': self.keyboard.id, 'quantity': 1}],
            discount_percentage=Decimal('0.00'),
            user=self.sales_user_1
        )

        client = Client()
        client.login(username='sales2_test', password='Password@123')

        response = client.get(f'/api/orders/{order.id}/')
        self.assertEqual(response.status_code, 403)
