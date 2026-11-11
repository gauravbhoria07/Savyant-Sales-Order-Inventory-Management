from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from masters.models import Customer, Product
from sales.models import SalesOrder

User = get_user_model()


class AuthenticationAndPermissionsTestCase(TestCase):
    """
    Test suite verifying authentication, password hashing, role enforcement,
    and access control across admin views, sales views, and REST APIs.
    """

    def setUp(self):
        self.client = Client()

        # Create Admin
        self.admin = User.objects.create_user(
            username='auth_admin',
            email='auth_admin@test.com',
            password='AdminPassword@123',
            role=User.Role.ADMIN
        )

        # Create Sales User 1
        self.sales_user_1 = User.objects.create_user(
            username='auth_sales1',
            email='auth_sales1@test.com',
            password='SalesPassword@123',
            role=User.Role.SALES_USER
        )

        # Create Sales User 2
        self.sales_user_2 = User.objects.create_user(
            username='auth_sales2',
            email='auth_sales2@test.com',
            password='SalesPassword@123',
            role=User.Role.SALES_USER
        )

        # Create Customer
        self.customer = Customer.objects.create(
            name='Test Client',
            mobile='9876543210',
            city='Delhi',
            status=Customer.Status.ACTIVE
        )

    def test_custom_user_roles_and_properties(self):
        """User model roles (ADMIN and SALES_USER) and helper properties must function properly."""
        self.assertTrue(self.admin.is_admin)
        self.assertFalse(self.admin.is_sales_user)

        self.assertTrue(self.sales_user_1.is_sales_user)
        self.assertFalse(self.sales_user_1.is_admin)

    def test_password_hashing(self):
        """Passwords must be hashed using Django's secure password hashers."""
        self.assertTrue(self.admin.check_password('AdminPassword@123'))
        self.assertFalse(self.admin.check_password('WrongPassword'))
        # Ensure password is not stored in plaintext
        self.assertNotEqual(self.admin.password, 'AdminPassword@123')
        self.assertTrue(self.admin.password.startswith('pbkdf2_') or self.admin.password.startswith('argon2'))

    def test_login_and_logout(self):
        """Users can successfully authenticate and log out."""
        # Valid login
        login_success = self.client.login(username='auth_admin', password='AdminPassword@123')
        self.assertTrue(login_success)

        # Dashboard accessible
        resp = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(resp.status_code, 200)

        # Logout
        resp_logout = self.client.get(reverse('logout'))
        self.assertRedirects(resp_logout, reverse('login'))

    def test_sales_user_blocked_from_admin_customer_creation(self):
        """Sales User cannot create or edit customer records (admin only)."""
        self.client.login(username='auth_sales1', password='SalesPassword@123')

        resp_create = self.client.get(reverse('masters:customer_create'))
        self.assertEqual(resp_create.status_code, 403)

        resp_post = self.client.post(reverse('masters:customer_create'), {
            'name': 'Unauthorized Customer',
            'mobile': '9000000000',
            'city': 'Mumbai',
            'status': 'ACTIVE',
        })
        self.assertEqual(resp_post.status_code, 403)

    def test_sales_user_blocked_from_admin_stock_adjustment(self):
        """Sales User cannot access manual stock adjustments."""
        self.client.login(username='auth_sales1', password='SalesPassword@123')

        resp = self.client.get(reverse('inventory:stock_adjustment'))
        self.assertEqual(resp.status_code, 403)

    def test_sales_user_blocked_from_admin_csv_import(self):
        """Sales User cannot access the CSV product import view."""
        self.client.login(username='auth_sales1', password='SalesPassword@123')

        resp = self.client.get(reverse('masters:product_import_csv'))
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_api_request_rejected(self):
        """Unauthenticated requests to protected REST API endpoints must be rejected."""
        client_anon = Client()
        resp = client_anon.get('/api/products/')
        # DRF returns 401 or 403 for unauthenticated access
        self.assertIn(resp.status_code, [401, 403])

        resp_order = client_anon.post('/api/orders/', {}, content_type='application/json')
        self.assertIn(resp_order.status_code, [401, 403])

    def test_api_sales_user_cannot_confirm_other_users_order(self):
        """Sales User cannot confirm another user's order via REST API."""
        order = SalesOrder.objects.create(
            customer=self.customer,
            created_by=self.sales_user_1
        )

        self.client.login(username='auth_sales2', password='SalesPassword@123')
        resp = self.client.post(f'/api/orders/{order.id}/confirm/')
        self.assertEqual(resp.status_code, 403)
        self.assertIn('Permission denied', resp.json().get('error', ''))
