# 5–8 Minute Technical Assessment Demo Video Script

**Candidate Name:** Fresher / Trainee Software Developer Candidate  
**Project:** Sales Order & Inventory Management System (Savyant Systems Technical Assignment)  
**Target Duration:** ~6 to 7 minutes  

---

## Video Outline & Timestamp Guide

| Time | Segment | Screen / Action to Display | Key Points to Explain |
|---|---|---|---|
| **0:00 – 0:45** | **1. Introduction & Architecture** | Project landing page & VS Code project tree | Tech stack (Python 3.13, Django 5.2, MySQL 8.0, Bootstrap 5). 6 decoupled apps. |
| **0:45 – 1:45** | **2. Role-Based Access Control** | Sign in as `admin`, then sign in as `sales1` | Admin vs. Sales User permissions. Backend security preventing cross-user order access. |
| **1:45 – 2:45** | **3. Product Management & CSV Import** | Product catalog & CSV Import page | Safe deletion rule. All-or-nothing CSV import demo with invalid vs. valid files. |
| **2:45 – 4:00** | **4. Sales Order Creation & JS** | Create Order page (`/sales/create/`) | Dynamic rows, live price/stock lookup, live total calculation, duplicate product prevention. |
| **4:00 – 5:15** | **5. Concurrency & Stock Logic** | Order detail (`/sales/<id>/`) & Inventory movements | `transaction.atomic()`, `select_for_update()`, stock deduction, cancellation restoration. |
| **5:15 – 6:15** | **6. Reports & Analytics** | Dashboard & Customer / Product Sales reports | Date range filtering, zero-order customer handling, configurable low stock threshold. |
| **6:15 – 7:00** | **7. Debugging Exercise & SQL Queries** | Terminal running tests & `sql_queries.sql` | 18 passing Django tests, 10 debugging exercise tests, 5 standalone SQL queries. |

---

## Detailed Spoken Script

### 1. Introduction & Overview (0:00 – 0:45)
> *"Hello! My name is Gaurav, and today I am demonstrating my submission for the Savyant Systems Fresher Software Developer technical assessment: the Sales Order & Inventory Management System.*  
>  
> *The application is built with Python 3.13 and Django 5.2 on top of MySQL 8.0 with InnoDB tables. For the frontend, I used Bootstrap 5 and vanilla JavaScript without heavy external frameworks to ensure clean, maintainable, beginner-friendly code.*  
>  
> *The project is organized into 6 focused applications: `accounts`, `masters`, `sales`, `inventory`, `reports`, and `config`."*

### 2. User Roles & Access Control (0:45 – 1:45)
> *"First, let's explore authentication and role enforcement.*  
>  
> *I'll sign in as `admin`. As an Admin, I have full access: I can manage customers and products, adjust stock manually, view all sales orders across the entire company, run reports, and import products via CSV.*  
>  
> *Now, let's log out and sign in as `sales1`, a Sales User. Notice the navbar automatically adjusts. Sales users can view active customers and products, and create their own sales orders. Most importantly, permissions are enforced strictly on the backend: if `sales1` attempts to modify the URL to access an order created by another user, Django raises a `403 PermissionDenied` error or returns HTTP 403 on the REST API."*

### 3. Product Catalog & All-or-Nothing CSV Import (1:45 – 2:45)
> *"Let's log back in as Admin and navigate to the Product Catalog.*  
>  
> *Products have check constraints ensuring price and stock quantity can never be negative. In addition, our safe deletion policy prevents deleting any customer or product that has order history or stock ledger movements.*  
>  
> *Now let's examine the CSV Import feature. The assignment requires all-or-nothing validation with row-numbered errors. If I upload `sample_products_invalid.csv`, the system analyzes every row and rejects the entire batch, reporting exact row numbers for the negative price, negative stock, and duplicate code. Nothing is written to the database.*  
>  
> *When I upload `sample_products_valid.csv`, all products are imported cleanly in a single transaction, and opening stock ledger entries are created automatically."*

### 4. Sales Order Creation & Client-Side JavaScript (2:45 – 4:00)
> *"Next, let's create a new sales order.*  
>  
> *On the order form, only active customers and active products can be selected. Notice our vanilla JavaScript in `order_form.js`:*  
> - *I can dynamically add and remove product rows without reloading.*  
> - *Selecting a product immediately fetches its current rate and available stock.*  
> - *Changing quantities or the discount percentage instantly updates item amounts, subtotal, discount, and grand total.*  
> - *If I attempt to select the same product twice, or enter a negative quantity, client-side validation warns me immediately.*  
> - *When I click 'Save as Draft', the submit button disables with a spinner to prevent accidental double submissions.*  
>  
> *Crucially, all totals and prices are recalculated securely on the server upon arrival — we never trust rates or totals from the browser."*

### 5. Concurrency-Safe Stock Logic (4:00 – 5:15)
> *"Now let's look at the heart of the system: Order Confirmation and Stock Control.*  
>  
> *In Draft state, stock is not yet reserved or deducted. When I click 'Confirm Order', a confirmation modal prompts me. Behind the scenes, the confirmation executes inside `transaction.atomic()` with `select_for_update()`. We sort the product IDs to eliminate database deadlocks.*  
>  
> *The system verifies that all products have sufficient stock. If even one product is short, the entire confirmation rolls back with a clear error message. If all products are sufficient, stock is deducted, the order becomes Confirmed, and immutable 'DISPATCH' entries are logged in the Stock Movement ledger.*  
>  
> *Confirmed orders are read-only. If we now click 'Cancel Order', the system safely restores all deducted stock and records 'RETURN' movements in the ledger. Repeated clicks cannot cause double deductions or double restorations."*

### 6. Reports & Business Intelligence (5:15 – 6:15)
> *"Under Reports, we have:*  
> 1. *The Executive Dashboard with high-level KPI cards and recent transactions.*  
> 2. *Customer Sales Summary: shows confirmed order count and net sales after discount, with date filtering. Notice it correctly includes customers with zero orders and avoids duplicate order counts.*  
> 3. *Product Sales Summary: displays total volume sold and gross value before order discount.*  
> 4. *Low Stock Report: highlights items below a configurable threshold (default 10 units) to assist procurement.*  
> 5. *Stock Movement History: a complete chronological audit trail."*

### 7. Debugging Exercise, Automated Tests & SQL (6:15 – 7:00)
> *"To conclude:*  
> - *In `debugging_exercise.py`, I diagnosed that the original function used `=` instead of `+=`, overwriting the accumulator. I implemented a robust version using Python `Decimal` with full validation for empty lists, missing keys, and invalid values, verified by 10 unit tests.*  
> - *In `sql_queries.sql`, I provided all 5 requested standalone queries using actual project schema names.*  
> - *Finally, running `python manage.py test` executes all 18 automated Django test cases against our MySQL database, covering calculations, stock rollback, permissions, and CSV imports.*  
>  
> *Thank you very much for your time and consideration. I look forward to discussing the project and answering any questions during the technical interview!"*
