from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from masters.models import Customer, Product
from sales.models import SalesOrder
from sales.services import create_sales_order
from inventory.models import StockMovement
from inventory.services import confirm_sales_order, cancel_sales_order, adjust_stock, InventoryError

User = get_user_model()


class InventoryManagementTestCase(TestCase):
    """
    Automated test suite verifying order confirmation, inventory consistency,
    cancellation stock restoration, and concurrency safety.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='inventory_admin',
            email='inv_admin@test.com',
            password='Password@123',
            role=User.Role.ADMIN
        )

        self.customer = Customer.objects.create(
            name='Global Logistics',
            email='info@globallogistics.com',
            mobile='9988776655',
            city='Mumbai',
            status=Customer.Status.ACTIVE
        )

        self.monitor = Product.objects.create(
            code='PRD-MON',
            name='24-inch Monitor',
            category='Displays',
            price=Decimal('12000.00'),
            stock_quantity=10,
            status=Product.Status.ACTIVE
        )

        self.hub = Product.objects.create(
            code='PRD-HUB',
            name='USB-C Hub',
            category='Accessories',
            price=Decimal('1500.00'),
            stock_quantity=5,
            status=Product.Status.ACTIVE
        )

    def test_confirmation_with_sufficient_stock(self):
        """Order confirmation deducts stock and records movement ledger entries."""
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=[
                {'product_id': self.monitor.id, 'quantity': 3},
                {'product_id': self.hub.id, 'quantity': 2},
            ],
            discount_percentage=Decimal('0.00'),
            user=self.user
        )

        confirmed_order = confirm_sales_order(order.id, self.user)
        self.assertEqual(confirmed_order.status, SalesOrder.Status.CONFIRMED)

        # Verify stock deductions
        self.monitor.refresh_from_db()
        self.hub.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 7) # 10 - 3
        self.assertEqual(self.hub.stock_quantity, 3)     # 5 - 2

        # Verify stock movement ledger
        movements = StockMovement.objects.filter(related_order=order)
        self.assertEqual(movements.count(), 2)
        for m in movements:
            self.assertEqual(m.movement_type, StockMovement.MovementType.DISPATCH)
            self.assertTrue(m.quantity_change < 0)

    def test_confirmation_with_one_insufficient_stock_causes_complete_rollback(self):
        """
        If even one item has insufficient stock, the entire confirmation MUST fail
        and rollback completely (all-or-nothing).
        """
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=[
                {'product_id': self.monitor.id, 'quantity': 2}, # sufficient (10 >= 2)
                {'product_id': self.hub.id, 'quantity': 10},    # INSUFFICIENT (only 5 available)
            ],
            discount_percentage=Decimal('0.00'),
            user=self.user
        )

        # Must raise InventoryError
        with self.assertRaises(InventoryError):
            confirm_sales_order(order.id, self.user)

        # Verify NOTHING was deducted (monitor remains 10, hub remains 5)
        self.monitor.refresh_from_db()
        self.hub.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 10)
        self.assertEqual(self.hub.stock_quantity, 5)

        # Order must remain in DRAFT status
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.DRAFT)

        # Zero movements should have been created
        self.assertEqual(StockMovement.objects.filter(related_order=order).count(), 0)

    def test_repeated_confirmation_does_not_deduct_stock_twice(self):
        """Repeated confirmation attempts on an already confirmed order must be rejected."""
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=[{'product_id': self.monitor.id, 'quantity': 2}],
            discount_percentage=Decimal('0.00'),
            user=self.user
        )

        confirm_sales_order(order.id, self.user)
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 8)

        # Second confirmation must raise InventoryError
        with self.assertRaises(InventoryError):
            confirm_sales_order(order.id, self.user)

        # Stock must NOT be deducted again
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 8)

    def test_cancellation_of_confirmed_order_restores_stock_once(self):
        """Cancelling a confirmed order restores deducted stock and logs return movements."""
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=[{'product_id': self.monitor.id, 'quantity': 4}],
            discount_percentage=Decimal('0.00'),
            user=self.user
        )
        confirm_sales_order(order.id, self.user)
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 6)

        # Cancel confirmed order
        cancelled_order = cancel_sales_order(order.id, self.user)
        self.assertEqual(cancelled_order.status, SalesOrder.Status.CANCELLED)

        # Stock should be restored to 10
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 10)

        # Return movement created
        return_mov = StockMovement.objects.filter(
            related_order=order,
            movement_type=StockMovement.MovementType.RETURN
        ).first()
        self.assertIsNotNone(return_mov)
        self.assertEqual(return_mov.quantity_change, 4)

        # Repeated cancellation must be rejected and not add stock again
        with self.assertRaises(InventoryError):
            cancel_sales_order(order.id, self.user)

        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 10)

    def test_cancellation_of_draft_order_does_not_modify_stock(self):
        """Cancelling a draft order transitions status to CANCELLED without touching stock."""
        order = create_sales_order(
            customer_id=self.customer.id,
            items_data=[{'product_id': self.monitor.id, 'quantity': 3}],
            discount_percentage=Decimal('0.00'),
            user=self.user
        )
        cancel_sales_order(order.id, self.user)

        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 10)
        self.assertEqual(StockMovement.objects.filter(related_order=order).count(), 0)

    def test_manual_stock_adjustment(self):
        """Manual adjustments increase or decrease stock and reject negative stock."""
        # Increase stock by 5
        adjust_stock(self.monitor.id, 'IN', 5, 'Received extra shipment', self.user)
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 15)

        # Decrease stock by 3
        adjust_stock(self.monitor.id, 'OUT', 3, 'Damaged units disposal', self.user)
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 12)

        # Try to decrease more than available stock (12 < 50)
        with self.assertRaises(InventoryError):
            adjust_stock(self.monitor.id, 'OUT', 50, 'Excess reduction', self.user)

        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.stock_quantity, 12)
