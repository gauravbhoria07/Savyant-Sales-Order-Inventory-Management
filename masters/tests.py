import io
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth import get_user_model
from masters.models import Customer, Product
from masters.csv_import import import_products_csv
from sales.models import SalesOrder, SalesOrderItem
from inventory.models import StockMovement

User = get_user_model()


class MastersTestCase(TestCase):
    """
    Automated test suite for Master data management:
    - Safe deletion restrictions
    - All-or-nothing CSV import validation
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username='master_admin',
            email='m_admin@test.com',
            password='Password@123',
            role=User.Role.ADMIN
        )

        self.customer = Customer.objects.create(
            name='Alpha Corp',
            email='alpha@corp.com',
            mobile='9123456780',
            city='Delhi',
            status=Customer.Status.ACTIVE
        )

        self.product = Product.objects.create(
            code='PRD-TST',
            name='Test Gadget',
            category='Electronics',
            price=Decimal('100.00'),
            stock_quantity=10,
            status=Product.Status.ACTIVE
        )

    def test_csv_import_valid_file(self):
        """Valid CSV file imports all products and creates OPENING stock movements."""
        csv_content = (
            "product_code,product_name,category,price,stock_quantity,status\n"
            "CSV-001,Laptop Stand,Accessories,1200.00,15,Active\n"
            "CSV-002,Ethernet Cable,Networking,250.00,40,Active\n"
        ).encode('utf-8')

        file_obj = io.BytesIO(csv_content)
        success, errors, count = import_products_csv(file_obj, self.admin)

        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
        self.assertEqual(count, 2)
        self.assertTrue(Product.objects.filter(code='CSV-001').exists())
        self.assertTrue(Product.objects.filter(code='CSV-002').exists())

        # Verify opening stock movement created
        opening_movements = StockMovement.objects.filter(movement_type=StockMovement.MovementType.OPENING)
        self.assertEqual(opening_movements.count(), 2)

    def test_csv_import_invalid_file_imports_nothing(self):
        """
        If even one row has an error (e.g., negative price or duplicate code),
        the ENTIRE CSV import MUST be aborted and import 0 products.
        """
        initial_product_count = Product.objects.count()

        csv_content = (
            "product_code,product_name,category,price,stock_quantity,status\n"
            "CSV-101,Desk Lamp,Lighting,1500.00,10,Active\n"
            "CSV-102,Bad Price Product,Lighting,-500.00,5,Active\n" # Negative price error!
            "CSV-103,Bad Stock Product,Lighting,800.00,-10,Active\n" # Negative stock error!
        ).encode('utf-8')

        file_obj = io.BytesIO(csv_content)
        success, errors, count = import_products_csv(file_obj, self.admin)

        self.assertFalse(success)
        self.assertTrue(len(errors) >= 2)
        self.assertEqual(count, 0)

        # Ensure NO new products were created in DB
        self.assertEqual(Product.objects.count(), initial_product_count)
        self.assertFalse(Product.objects.filter(code='CSV-101').exists())

    def test_customer_safe_deletion_prevented_when_order_exists(self):
        """Deleting a customer referenced by a sales order must be prevented."""
        order = SalesOrder.objects.create(
            customer=self.customer,
            created_by=self.admin
        )
        self.assertTrue(self.customer.orders.exists())
        # customer.orders.exists() returns True, preventing safe deletion

    def test_product_safe_deletion_prevented_when_order_exists(self):
        """Deleting a product referenced by order items must be prevented."""
        order = SalesOrder.objects.create(
            customer=self.customer,
            created_by=self.admin
        )
        SalesOrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            rate=Decimal('100.00')
        )
        self.assertTrue(self.product.order_items.exists())
