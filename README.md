# Sales Order & Inventory Management System

A robust, beginner-friendly, production-ready Django web application developed for the **Savyant Systems Technical Assessment (Fresher / Trainee Software Developer)**.

Built with Python 3.13, Django 5.2, Django REST Framework, and MySQL 8.0 (InnoDB), this system automates customer management, product cataloging, multi-item sales orders with server-calculated discounts, transactional concurrency-safe inventory tracking, comprehensive sales reports, CSV bulk imports, and authenticated REST APIs.

---

## 1. Technology Stack

- **Backend:** Python 3.13, Django 5.2.4
- **API Framework:** Django REST Framework (DRF 3.18)
- **Database:** MySQL 8.0 (InnoDB storage engine for transactional integrity and row locking)
- **Database Drivers:** `mysqlclient` (primary) and `PyMySQL` (compatible fallback)
- **Frontend:** HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Vanilla JavaScript
- **Version Control:** Git & GitHub
- **Testing:** Django TestCase & Python standard `unittest`

---

## 2. Project Structure

The project strictly follows a clean, decoupled 6-app Django architecture:

```text
job proj/
├── config/                     # Django project root settings and main URL dispatcher
│   ├── __init__.py             # Database driver initializations
│   ├── settings.py             # App configurations, Auth model, MySQL DB settings
│   ├── urls.py                 # Routing table for apps and /api/ endpoints
│   └── wsgi.py
├── accounts/                   # Authentication & user role enforcement
│   ├── models.py               # Custom User model (ADMIN & SALES_USER)
│   ├── permissions.py          # View decorators and DRF permission classes
│   ├── forms.py                # Bootstrap login form
│   ├── views.py                # Login and logout views
│   ├── management/commands/    # python manage.py seed_data command
│   └── urls.py
├── masters/                    # Master records
│   ├── models.py               # Customer & Product entities with check constraints
│   ├── forms.py                # Customer & Product forms with validation
│   ├── views.py                # CRUD views for customers and products
│   ├── csv_import.py           # All-or-nothing CSV import engine
│   ├── serializers.py          # DRF serializers for Product & Customer
│   ├── tests.py                # Safe deletion & CSV validation tests
│   └── urls.py
├── sales/                      # Sales order management
│   ├── models.py               # SalesOrder & SalesOrderItem models
│   ├── services.py             # Order validation and server-side calculation logic
│   ├── views.py                # Order listing, detail, creation, confirmation & cancellation
│   ├── api.py                  # Authenticated REST API views
│   ├── serializers.py          # Serializers for orders and order items
│   ├── tests.py                # Financial calculation, discount, & permission tests
│   └── urls.py
├── inventory/                  # Stock control and audit ledger
│   ├── models.py               # StockMovement audit ledger
│   ├── services.py             # Concurrency-safe atomic stock deduction & restoration
│   ├── views.py                # Manual stock adjustments and movement history
│   ├── tests.py                # Concurrency, rollback, and adjustment tests
│   └── urls.py
├── reports/                    # Business intelligence and executive reports
│   ├── views.py                # Dashboard, Customer Sales, Product Sales, Low Stock reports
│   └── urls.py
├── static/                     # Static styling and JavaScript
│   ├── css/custom.css          # Custom styling and badge colors
│   └── js/order_form.js        # Vanilla JS: dynamic rows, live totals, duplicate checks
├── templates/                  # Bootstrap 5 HTML templates organized by app
├── sample_products_valid.csv   # Valid CSV sample for demonstration
├── sample_products_invalid.csv # Invalid CSV sample testing row-level error reporting
├── sql_queries.sql             # 5 Standalone SQL queries for assignment evaluation
├── debugging_exercise.py       # Standalone debugging exercise and unit tests
├── AI_USAGE.md                 # AI disclosure, prompt samples, and review documentation
├── DEMO_SCRIPT.md              # 5-8 minute technical interview walkthrough script
├── requirements.txt            # Dependency specification
├── .env.example                # Template for environment variables
└── manage.py
```

---

## 3. Database Schema & Entity Relationships

```text
+-----------------------+              +-----------------------+
|     accounts_user     |              |    masters_customer   |
+-----------------------+              +-----------------------+
| id (PK)               |              | id (PK)               |
| username (Unique)     |              | name                  |
| email (Unique)        |              | email                 |
| password              |              | mobile                |
| role (ADMIN/SALES)    |              | city                  |
+-----------+-----------+              | status (ACTIVE/INACT) |
            |                          +-----------+-----------+
            | 1                                    | 1
            |                                      |
            | creates                              | places
            | N                                    | N
+-----------v--------------------------------------v-----------+
|                       sales_salesorder                       |
+--------------------------------------------------------------+
| id (PK)                                                      |
| order_number (Unique, Auto-generated)                        |
| customer_id (FK -> masters_customer, on_delete=PROTECT)      |
| created_by_id (FK -> accounts_user, on_delete=PROTECT)       |
| order_date                                                   |
| status (DRAFT / CONFIRMED / CANCELLED)                       |
| discount_percentage (0.00% to 20.00%)                        |
| subtotal (Decimal)                                           |
| discount_amount (Decimal)                                    |
| grand_total (Decimal)                                        |
+------------------------------+-------------------------------+
                               | 1
                               | has
                               | N
+------------------------------v-------------------------------+
|                     sales_salesorderitem                     |
+--------------------------------------------------------------+
| id (PK)                                                      |
| order_id (FK -> sales_salesorder, on_delete=CASCADE)         |
| product_id (FK -> masters_product, on_delete=PROTECT)        |
| quantity (Positive integer >= 1)                             |
| rate (Decimal snapshot at order time)                        |
| amount (Decimal = quantity * rate)                           |
+------------------------------+-------------------------------+
                               | N
                               | references
                               | 1
+------------------------------v-------------------------------+
|                       masters_product                        |
+--------------------------------------------------------------+
| id (PK)                                                      |
| code (Unique, e.g. PRD-001)                                  |
| name                                                         |
| category                                                     |
| price (Decimal >= 0.00, CheckConstraint)                     |
| stock_quantity (Positive Integer >= 0, CheckConstraint)      |
| status (ACTIVE / INACTIVE)                                   |
+------------------------------+-------------------------------+
                               | 1
                               | audit tracked by
                               | N
+------------------------------v-------------------------------+
|                    inventory_stockmovement                   |
+--------------------------------------------------------------+
| id (PK)                                                      |
| product_id (FK -> masters_product, on_delete=PROTECT)        |
| movement_type (IN / OUT / DISPATCH / RETURN / OPENING)       |
| quantity_change (Signed integer, e.g. -2, +5)                |
| related_order_id (FK -> sales_salesorder, NULL allowed)      |
| reason (Mandatory audit explanation)                         |
| created_by_id (FK -> accounts_user, on_delete=PROTECT)       |
| timestamp (Auto-generated datetime)                          |
+--------------------------------------------------------------+
```

### Key Relational Design Decisions:
1. **Rate Snapshotting:** `SalesOrderItem.rate` freezes the product price at the time of order creation. Future price revisions on the product will **never** alter past financial history.
2. **Safe Deletions (`on_delete=models.PROTECT`):** Customers and products referenced by existing orders cannot be deleted from the database. The system requires deactivating them (`INACTIVE`) instead.
3. **Check Constraints:** Enforced at the database level (`price >= 0`, `stock_quantity >= 0`, `quantity >= 1`).
4. **Unique Constraints:** `unique_product_per_order` prevents the same product from being added multiple times within one order.

---

## 4. Role-Based Permissions (Server-Enforced)

The system distinguishes two roles in `accounts.models.User.Role`:

| Feature / Action | Admin | Sales User | Backend Enforcement |
|---|:---:|:---:|---|
| **View Active Customers & Products** | Yes | Yes | Filtered by `status='ACTIVE'` for Sales Users |
| **Create / Edit / Delete Masters** | Yes | **No** | `@admin_required` decorator & `IsAdminUserRole` |
| **Import Products via CSV** | Yes | **No** | Admin-only route and permission checks |
| **Create Sales Orders (Draft)** | Yes | Yes | Authenticated users |
| **View Orders List** | All Orders | **Own Orders Only** | Queryset filtered by `created_by=request.user` |
| **View / Manage Order Detail** | All Orders | **Own Orders Only** | Returns `403 Forbidden` if Sales User alters URL ID |
| **Confirm / Cancel Orders** | Yes | **Own Orders Only** | Backend permission check in service layer |
| **Manual Stock Adjustment** | Yes | **No** | `@admin_required` decorator |
| **View Financial Reports** | Yes | Yes | Confirmed orders only |

---

## 5. Inventory & Concurrency Management

When an order is confirmed:
1. An atomic database transaction begins (`transaction.atomic()`).
2. Order row is locked with `select_for_update()` to prevent double confirmations.
3. If order status is not `DRAFT`, confirmation is immediately rejected.
4. All involved products are locked via `Product.objects.select_for_update()`, sorted by product ID to eliminate database deadlocks.
5. **Stock Sufficiency Verification:** The system checks available stock for every product. If even a single item is short by 1 unit, the **entire** confirmation is rejected, no stock is deducted, and the transaction rolls back cleanly.
6. **Stock Deduction & Audit Trail:** If all items are sufficient, stock is deducted from each product, and immutable `StockMovement` records (type: `DISPATCH`, negative quantity) are logged.
7. Order status transitions to `CONFIRMED`.

When a confirmed order is cancelled:
1. `transaction.atomic()` locks products with `select_for_update()`.
2. Exact quantities are added back to product stock.
3. `StockMovement` records (type: `RETURN`, positive quantity) are logged.
4. Order status transitions to `CANCELLED` (terminal state; read-only).
5. If already cancelled, repeated cancellation attempts are rejected idempotently.

---

## 6. Installation & Setup Guide

### Prerequisites
- Python 3.13 (or 3.11+)
- MySQL Server 8.0 running locally on port 3306
- Git

### Step 1: Clone or Navigate to Project
```bash
cd "D:\job proj"
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Update `.env` with your local MySQL credentials:
```ini
SECRET_KEY=your-secure-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.mysql
DB_NAME=sales_inventory_db
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### Step 5: Create MySQL Database
Log in to MySQL and create the database if not already created:
```sql
CREATE DATABASE IF NOT EXISTS sales_inventory_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 6: Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 7: Seed Sample Data
Run the built-in seeding command to populate realistic demo data:
```bash
python manage.py seed_data
```

This automatically sets up:
- **Admin account:** Username: `admin` | Password: `Admin@123`
- **Sales User 1:** Username: `sales1` | Password: `Sales@123`
- **Sales User 2:** Username: `sales2` | Password: `Sales@123`
- 6 Customers (including an inactive customer and a customer with zero orders)
- 7 Products (including low-stock products)
- Realistic sales orders in Draft, Confirmed, and Cancelled states with stock movements

### Step 8: Start Development Server
```bash
python manage.py runserver
```
Open your browser and navigate to: **`http://127.0.0.1:8000/`**

---

## 7. REST API Documentation

All API endpoints require authentication (Session or Basic Auth).

### 1. List Active Products
- **Method:** `GET`
- **URL:** `/api/products/?search=keyboard`
- **Response `200 OK`:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "PRD-001",
      "name": "Mechanical Gaming Keyboard",
      "category": "Accessories",
      "price": "1500.00",
      "stock_quantity": 38,
      "status": "ACTIVE"
    }
  ]
}
```

### 2. Create Draft Sales Order
- **Method:** `POST`
- **URL:** `/api/orders/`
- **Request Body:**
```json
{
  "customer_id": 1,
  "discount_percentage": "10.00",
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 2, "quantity": 3}
  ]
}
```
- **Response `201 Created`:**
```json
{
  "id": 5,
  "order_number": "SO-20261109-7AB1C2",
  "customer": {
    "id": 1,
    "name": "Apex Technologies Pvt Ltd",
    "email": "procurement@apextech.in",
    "mobile": "9876543210",
    "city": "Bengaluru",
    "status": "ACTIVE"
  },
  "order_date": "2026-11-09",
  "status": "DRAFT",
  "discount_percentage": "10.00",
  "subtotal": "4500.00",
  "discount_amount": "450.00",
  "grand_total": "4050.00",
  "created_by_username": "sales1",
  "created_at": "2026-11-09T17:15:00Z",
  "items": [
    {
      "id": 8,
      "product": 1,
      "product_code": "PRD-001",
      "product_name": "Mechanical Gaming Keyboard",
      "quantity": 2,
      "rate": "1500.00",
      "amount": "3000.00"
    },
    {
      "id": 9,
      "product": 2,
      "product_code": "PRD-002",
      "product_name": "Ergonomic Wireless Mouse",
      "quantity": 3,
      "rate": "500.00",
      "amount": "1500.00"
    }
  ]
}
```

### 3. Retrieve Sales Order
- **Method:** `GET`
- **URL:** `/api/orders/5/`
- **Access Rule:** Sales users can only retrieve their own orders. Attempting to view another user's order returns:
- **Response `403 Forbidden`:**
```json
{
  "error": "Permission denied. You cannot access orders created by another user."
}
```

### 4. Confirm Sales Order
- **Method:** `POST`
- **URL:** `/api/orders/5/confirm/`
- **Response `200 OK` (Sufficient Stock):**
```json
{
  "message": "Order SO-20261109-7AB1C2 confirmed successfully.",
  "order": { ... }
}
```
- **Response `400 Bad Request` (Insufficient Stock):**
```json
{
  "error": "Insufficient stock for: USB-C Dual HDMI Hub (Available: 5, Required: 10). No changes were made."
}
```

### 5. Cancel Sales Order
- **Method:** `POST`
- **URL:** `/api/orders/5/cancel/`
- **Response `200 OK`:**
```json
{
  "message": "Order SO-20261109-7AB1C2 cancelled successfully.",
  "order": { ... }
}
```

---

## 8. Automated Testing

### Test Suite Coverage (32 Comprehensive Tests):
- **Calculations & Discounts (`sales/tests.py`):** Verifies multi-item order totaling, discount percentage application (0–20%), snapshot rate freezing, and `Decimal` rounding.
- **Defensive Rejections (`sales/tests.py`):** Zero quantity, negative quantity, invalid discount (>20% or <0%), and duplicate products within an order are rejected.
- **Stock Management (`inventory/tests.py`):** Sufficient stock deduction, all-or-nothing rollback on insufficient stock, and idempotent repeated confirmation.
- **Stock Restoration (`inventory/tests.py`):** Cancelling confirmed orders restores stock once; cancelling draft orders does not change stock.
- **Role Isolation & Auth (`accounts/tests.py`):** Password hashing checks, role properties, Sales User blocked from Admin customer/product/stock views with `403 Forbidden`, and unauthenticated API calls rejected with `401/403`.
- **Sales User Order Ownership (`sales/tests.py`):** Sales User accessing another user's order in web views or API is denied with `403 Forbidden`.
- **Safe Deletion & CSV Import (`masters/tests.py`):** Safe deletion restrictions prevent deleting referenced customers/products; all-or-nothing rollback when an invalid CSV row is present, and full import with opening stock when valid.
- **Reports & Aggregation Regression (`reports/tests.py`):**
  - **Identical Grand Totals Regression Test:** Verifies that multiple confirmed orders with identical grand totals are all included in customer total sales (not dropped by `DISTINCT`).
  - **Zero-Order Customers:** Verifies customers with zero orders display count 0 and total 0.00.
  - **Date Range Filters:** Verifies orders outside the date filter are excluded.
  - **Draft/Cancelled Exclusion:** Verifies unconfirmed orders do not inflate report metrics.
  - **Product Sales & Low Stock:** Verifies volume, gross value, and configurable threshold filtering.

### Running Automated Tests:
```bash
python manage.py test
```

### Running the Debugging Exercise Tests:
```bash
python debugging_exercise.py
```
*(Runs 10 dedicated unittests covering accumulator bugs, empty lists, missing keys, and invalid types).*

---

## 9. Standalone SQL Queries (`sql_queries.sql`)

The repository includes `sql_queries.sql` containing the exact 5 queries:
1. **Top 3 Customers:** By Confirmed order grand total revenue.
2. **Top 3 Products:** By quantity sold in Confirmed orders.
3. **Zero-Order Customers:** Left join identifying customers who never placed an order.
4. **Month-Wise Sales:** Sales grouped by `YEAR(order_date)` and `MONTH(order_date)`.
5. **Low Stock Products:** Products where `stock_quantity <= 10`.

---

## 10. MCA Technical Interview Preparation Guide

When explaining this project in your interview:
1. **Stock Concurrency:** Explain why you chose `transaction.atomic()` combined with `select_for_update()`. Mention that sorting product IDs (`sorted([p.id ...])`) prevents deadlock under high concurrency.
2. **Financial Precision:** Emphasize that monetary values use Python's `Decimal` with `ROUND_HALF_UP` rather than `float` to avoid IEEE 754 floating-point inaccuracies.
3. **Server-Side Trust:** Explain that client-side JavaScript provides immediate user feedback, but all rates, item amounts, discounts, and totals are re-fetched and computed on the backend.
4. **All-or-Nothing Transactions:** Explain that both Order Confirmation and CSV Import use atomic transactions so partial updates never corrupt database state.
