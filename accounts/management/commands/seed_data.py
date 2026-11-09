from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from masters.models import Customer, Product
from sales.models import SalesOrder, SalesOrderItem
from sales.services import create_sales_order
from inventory.models import StockMovement
from inventory.services import confirm_sales_order, cancel_sales_order

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds database with demo users, customers, products, orders, and stock ledger entries."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Seeding Sales Order & Inventory Management System..."))

        # 1. Create Users
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@savyant.com',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('Admin@123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created Admin user: admin / Admin@123"))
        else:
            self.stdout.write("Admin user already exists.")

        sales_user1, created = User.objects.get_or_create(
            username='sales1',
            defaults={
                'email': 'sales1@savyant.com',
                'role': User.Role.SALES_USER,
            }
        )
        if created:
            sales_user1.set_password('Sales@123')
            sales_user1.save()
            self.stdout.write(self.style.SUCCESS("Created Sales user: sales1 / Sales@123"))

        sales_user2, created = User.objects.get_or_create(
            username='sales2',
            defaults={
                'email': 'sales2@savyant.com',
                'role': User.Role.SALES_USER,
            }
        )
        if created:
            sales_user2.set_password('Sales@123')
            sales_user2.save()
            self.stdout.write(self.style.SUCCESS("Created Sales user: sales2 / Sales@123"))

        # 2. Create Customers
        customers_data = [
            {'name': 'Apex Technologies Pvt Ltd', 'email': 'procurement@apextech.in', 'mobile': '9876543210', 'city': 'Bengaluru', 'status': Customer.Status.ACTIVE},
            {'name': 'Metro Infotech Solutions', 'email': 'sales@metroinfotech.com', 'mobile': '9823456781', 'city': 'Mumbai', 'status': Customer.Status.ACTIVE},
            {'name': 'Sunrise Hardware Mart', 'email': 'sunrise@hardware.com', 'mobile': '9712345678', 'city': 'Pune', 'status': Customer.Status.ACTIVE},
            {'name': 'Zenith Enterprises', 'email': 'contact@zenithenterprises.org', 'mobile': '9654321098', 'city': 'Hyderabad', 'status': Customer.Status.ACTIVE},
            {'name': 'Evergreen Retailers (Zero Orders)', 'email': 'evergreen@retail.in', 'mobile': '9543216789', 'city': 'Chennai', 'status': Customer.Status.ACTIVE},
            {'name': 'Old Legacy Traders', 'email': 'legacy@traders.com', 'mobile': '9432198765', 'city': 'Delhi', 'status': Customer.Status.INACTIVE},
        ]

        created_customers = {}
        for c in customers_data:
            cust, _ = Customer.objects.get_or_create(
                name=c['name'],
                defaults={
                    'email': c['email'],
                    'mobile': c['mobile'],
                    'city': c['city'],
                    'status': c['status'],
                }
            )
            created_customers[c['name']] = cust

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_customers)} customers."))

        # 3. Create Products
        products_data = [
            {'code': 'PRD-001', 'name': 'Mechanical Gaming Keyboard', 'category': 'Accessories', 'price': Decimal('1500.00'), 'stock': 40, 'status': Product.Status.ACTIVE},
            {'code': 'PRD-002', 'name': 'Ergonomic Wireless Mouse', 'category': 'Accessories', 'price': Decimal('500.00'), 'stock': 75, 'status': Product.Status.ACTIVE},
            {'code': 'PRD-003', 'name': '27-inch IPS UltraHD Monitor', 'category': 'Displays', 'price': Decimal('18500.00'), 'stock': 8, 'status': Product.Status.ACTIVE}, # Low stock
            {'code': 'PRD-004', 'name': 'USB-C Dual HDMI Hub', 'category': 'Accessories', 'price': Decimal('2200.00'), 'stock': 5, 'status': Product.Status.ACTIVE},   # Low stock
            {'code': 'PRD-005', 'name': 'Noise Cancelling Headset', 'category': 'Audio', 'price': Decimal('3400.00'), 'stock': 25, 'status': Product.Status.ACTIVE},
            {'code': 'PRD-006', 'name': 'CAT-6 High Speed Cable (10m)', 'category': 'Cables', 'price': Decimal('350.00'), 'stock': 120, 'status': Product.Status.ACTIVE},
            {'code': 'PRD-007', 'name': 'Discontinued VGA Cable', 'category': 'Cables', 'price': Decimal('120.00'), 'stock': 0, 'status': Product.Status.INACTIVE},
        ]

        created_products = {}
        for p in products_data:
            prod, created = Product.objects.get_or_create(
                code=p['code'],
                defaults={
                    'name': p['name'],
                    'category': p['category'],
                    'price': p['price'],
                    'stock_quantity': p['stock'],
                    'status': p['status'],
                }
            )
            created_products[p['code']] = prod
            if created and p['stock'] > 0:
                StockMovement.objects.create(
                    product=prod,
                    movement_type=StockMovement.MovementType.OPENING,
                    quantity_change=p['stock'],
                    reason="Initial opening stock setup",
                    created_by=admin_user,
                )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_products)} products with opening stock."))

        # 4. Create Sample Orders
        # Order 1: Confirmed order with 2 items and 10% discount
        if not SalesOrder.objects.filter(customer=created_customers['Apex Technologies Pvt Ltd']).exists():
            order1 = create_sales_order(
                customer_id=created_customers['Apex Technologies Pvt Ltd'].id,
                items_data=[
                    {'product_id': created_products['PRD-001'].id, 'quantity': 2},
                    {'product_id': created_products['PRD-002'].id, 'quantity': 3},
                ],
                discount_percentage=Decimal('10.00'),
                user=sales_user1
            )
            confirm_sales_order(order1.id, sales_user1)
            self.stdout.write(self.style.SUCCESS(f"Created Confirmed Order 1: {order1.order_number} (Grand Total: ₹{order1.grand_total})"))

        # Order 2: Confirmed order for Metro Infotech
        if not SalesOrder.objects.filter(customer=created_customers['Metro Infotech Solutions']).exists():
            order2 = create_sales_order(
                customer_id=created_customers['Metro Infotech Solutions'].id,
                items_data=[
                    {'product_id': created_products['PRD-003'].id, 'quantity': 1},
                    {'product_id': created_products['PRD-005'].id, 'quantity': 2},
                ],
                discount_percentage=Decimal('5.00'),
                user=sales_user2
            )
            confirm_sales_order(order2.id, sales_user2)
            self.stdout.write(self.style.SUCCESS(f"Created Confirmed Order 2: {order2.order_number} (Grand Total: ₹{order2.grand_total})"))

        # Order 3: Draft order for Sunrise Hardware
        if not SalesOrder.objects.filter(customer=created_customers['Sunrise Hardware Mart']).exists():
            order3 = create_sales_order(
                customer_id=created_customers['Sunrise Hardware Mart'].id,
                items_data=[
                    {'product_id': created_products['PRD-006'].id, 'quantity': 10},
                    {'product_id': created_products['PRD-002'].id, 'quantity': 5},
                ],
                discount_percentage=Decimal('0.00'),
                user=sales_user1
            )
            self.stdout.write(self.style.SUCCESS(f"Created Draft Order 3: {order3.order_number}"))

        # Order 4: Cancelled order for Zenith Enterprises
        if not SalesOrder.objects.filter(customer=created_customers['Zenith Enterprises']).exists():
            order4 = create_sales_order(
                customer_id=created_customers['Zenith Enterprises'].id,
                items_data=[
                    {'product_id': created_products['PRD-005'].id, 'quantity': 1},
                ],
                discount_percentage=Decimal('0.00'),
                user=sales_user2
            )
            confirm_sales_order(order4.id, sales_user2)
            cancel_sales_order(order4.id, sales_user2)
            self.stdout.write(self.style.SUCCESS(f"Created Cancelled Order 4: {order4.order_number}"))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
