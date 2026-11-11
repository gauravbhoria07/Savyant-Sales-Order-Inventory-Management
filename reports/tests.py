from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from masters.models import Customer, Product
from sales.models import SalesOrder, SalesOrderItem
from sales.services import create_sales_order
from inventory.services import confirm_sales_order, cancel_sales_order

User = get_user_model()


class ReportsTestCase(TestCase):
    """
    Test suite for sales and inventory reports, including regression tests
    for identical grand-total order summation and date-range filtering.
    """

    def setUp(self):
        self.client = Client()

        # Users
        self.admin = User.objects.create_user(
            username='reports_admin',
            email='rep_admin@test.com',
            password='Password@123',
            role=User.Role.ADMIN
        )
        self.sales_user = User.objects.create_user(
            username='reports_sales',
            email='rep_sales@test.com',
            password='Password@123',
            role=User.Role.SALES_USER
        )

        # Customers
        self.customer_a = Customer.objects.create(
            name='Alpha Corp',
            email='alpha@corp.com',
            mobile='9111111111',
            city='Bangalore',
            status=Customer.Status.ACTIVE
        )
        self.customer_zero = Customer.objects.create(
            name='Zero Orders Ltd',
            email='zero@orders.com',
            mobile='9222222222',
            city='Chennai',
            status=Customer.Status.ACTIVE
        )

        # Products
        self.product_a = Product.objects.create(
            code='REP-001',
            name='Product Alpha',
            category='Hardware',
            price=Decimal('500.00'),
            stock_quantity=100,
            status=Product.Status.ACTIVE
        )
        self.product_b = Product.objects.create(
            code='REP-002',
            name='Product Beta',
            category='Hardware',
            price=Decimal('1000.00'),
            stock_quantity=5,  # Low stock (<= 10)
            status=Product.Status.ACTIVE
        )

    def test_customer_sales_summary_with_identical_grand_totals(self):
        """
        REGRESSION TEST:
        Verify that when a customer has two separate confirmed orders with the EXACT same
        grand total, both orders are summed correctly (not deduplicated by a DISTINCT aggregate).
        """
        # Order 1: 1 unit of Product A = 500.00, 0% discount -> Grand Total = 500.00
        order1 = create_sales_order(
            customer_id=self.customer_a.id,
            items_data=[{'product_id': self.product_a.id, 'quantity': 1}],
            discount_percentage=Decimal('0.00'),
            user=self.sales_user
        )
        confirm_sales_order(order1.id, self.admin)

        # Order 2: 1 unit of Product A = 500.00, 0% discount -> Grand Total = 500.00 (identical!)
        order2 = create_sales_order(
            customer_id=self.customer_a.id,
            items_data=[{'product_id': self.product_a.id, 'quantity': 1}],
            discount_percentage=Decimal('0.00'),
            user=self.sales_user
        )
        confirm_sales_order(order2.id, self.admin)

        self.assertEqual(order1.grand_total, Decimal('500.00'))
        self.assertEqual(order2.grand_total, Decimal('500.00'))

        self.client.login(username='reports_admin', password='Password@123')
        response = self.client.get(reverse('reports:customer_sales_summary'))
        self.assertEqual(response.status_code, 200)

        # In context, find customer_a
        customers_in_report = {c.id: c for c in response.context['customers']}
        c_summary = customers_in_report[self.customer_a.id]

        # Order count must be 2
        self.assertEqual(c_summary.confirmed_order_count, 2)
        # Total sales MUST be 1000.00 (500 + 500), NOT 500.00!
        self.assertEqual(c_summary.total_sales, Decimal('1000.00'))

    def test_customer_sales_summary_includes_zero_order_customers(self):
        """Customers with zero confirmed orders must appear with count 0 and total 0.00."""
        self.client.login(username='reports_admin', password='Password@123')
        response = self.client.get(reverse('reports:customer_sales_summary'))
        self.assertEqual(response.status_code, 200)

        customers_in_report = {c.id: c for c in response.context['customers']}
        self.assertIn(self.customer_zero.id, customers_in_report)
        zero_cust = customers_in_report[self.customer_zero.id]
        self.assertEqual(zero_cust.confirmed_order_count, 0)
        self.assertEqual(zero_cust.total_sales, Decimal('0.00'))

    def test_customer_sales_summary_date_filtering(self):
        """Only orders within the filtered date range should be included."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)

        # Order placed yesterday
        order = create_sales_order(
            customer_id=self.customer_a.id,
            items_data=[{'product_id': self.product_a.id, 'quantity': 2}],
            discount_percentage=Decimal('0.00'),
            user=self.sales_user
        )
        order.order_date = yesterday
        order.save(update_fields=['order_date'])
        confirm_sales_order(order.id, self.admin)

        self.client.login(username='reports_admin', password='Password@123')

        # Filter for range covering yesterday
        resp = self.client.get(reverse('reports:customer_sales_summary'), {
            'start_date': str(last_week),
            'end_date': str(today)
        })
        cust = next(c for c in resp.context['customers'] if c.id == self.customer_a.id)
        self.assertEqual(cust.confirmed_order_count, 1)
        self.assertEqual(cust.total_sales, Decimal('1000.00'))

        # Filter for range in the past that does not include yesterday
        resp_past = self.client.get(reverse('reports:customer_sales_summary'), {
            'start_date': str(today - timedelta(days=30)),
            'end_date': str(today - timedelta(days=15))
        })
        cust_past = next(c for c in resp_past.context['customers'] if c.id == self.customer_a.id)
        self.assertEqual(cust_past.confirmed_order_count, 0)
        self.assertEqual(cust_past.total_sales, Decimal('0.00'))

    def test_draft_and_cancelled_orders_excluded_from_sales_summary(self):
        """Draft and Cancelled orders must never contribute to confirmed sales figures."""
        # Draft order
        draft_order = create_sales_order(
            customer_id=self.customer_a.id,
            items_data=[{'product_id': self.product_a.id, 'quantity': 1}],
            discount_percentage=Decimal('0.00'),
            user=self.sales_user
        )

        # Cancelled order
        cancelled_order = create_sales_order(
            customer_id=self.customer_a.id,
            items_data=[{'product_id': self.product_a.id, 'quantity': 1}],
            discount_percentage=Decimal('0.00'),
            user=self.sales_user
        )
        confirm_sales_order(cancelled_order.id, self.admin)
        cancel_sales_order(cancelled_order.id, self.admin)

        self.client.login(username='reports_admin', password='Password@123')
        resp = self.client.get(reverse('reports:customer_sales_summary'))
        cust = next(c for c in resp.context['customers'] if c.id == self.customer_a.id)
        self.assertEqual(cust.confirmed_order_count, 0)
        self.assertEqual(cust.total_sales, Decimal('0.00'))

    def test_product_sales_summary(self):
        """Product sales summary should calculate total sold units and gross value accurately."""
        order = create_sales_order(
            customer_id=self.customer_a.id,
            items_data=[
                {'product_id': self.product_a.id, 'quantity': 3},  # 3 * 500 = 1500
                {'product_id': self.product_b.id, 'quantity': 2},  # 2 * 1000 = 2000
            ],
            discount_percentage=Decimal('10.00'),
            user=self.sales_user
        )
        confirm_sales_order(order.id, self.admin)

        self.client.login(username='reports_admin', password='Password@123')
        resp = self.client.get(reverse('reports:product_sales_summary'))
        self.assertEqual(resp.status_code, 200)

        products_map = {p.id: p for p in resp.context['products']}
        prod_a_summary = products_map[self.product_a.id]
        self.assertEqual(prod_a_summary.total_quantity_sold, 3)
        self.assertEqual(prod_a_summary.gross_sales_value, Decimal('1500.00'))

    def test_low_stock_report_configurable_threshold(self):
        """Low stock report should show products with stock <= threshold."""
        self.client.login(username='reports_admin', password='Password@123')

        # Product Beta has stock 5, Product Alpha has stock 100
        # Default threshold is 10 -> Product Beta matches
        resp = self.client.get(reverse('reports:low_stock_report'))
        self.assertEqual(resp.status_code, 200)
        matched_ids = [p.id for p in resp.context['products']]
        self.assertIn(self.product_b.id, matched_ids)
        self.assertNotIn(self.product_a.id, matched_ids)

        # Set threshold to 150 -> both match
        resp2 = self.client.get(reverse('reports:low_stock_report'), {'threshold': '150'})
        matched_ids2 = [p.id for p in resp2.context['products']]
        self.assertIn(self.product_a.id, matched_ids2)
        self.assertIn(self.product_b.id, matched_ids2)
