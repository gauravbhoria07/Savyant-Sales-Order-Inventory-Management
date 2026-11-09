# AI Usage Disclosure (AI_USAGE.md)

In accordance with Part 14 of the Savyant Systems Technical Assignment guidelines, this document discloses the utilization of AI assistance during the development of the **Sales Order & Inventory Management System**.

---

## 1. Tools Used

- **AI Coding Assistant:** Google Antigravity / Gemini 3.8 Flash (High)
- **Role:** Interactive pair-programming assistant for boilerplate scaffolding, test generation, and review.

---

## 2. Tasks Assisted by AI

1. **Architecture & Scaffolding:** Structuring the Django project into 6 domain-driven apps (`accounts`, `masters`, `sales`, `inventory`, `reports`, `config`).
2. **Bootstrap 5 UI Layouts:** Writing clean HTML templates, modal dialogs, and responsive navigation.
3. **Vanilla JavaScript Implementation:** Authoring `order_form.js` to manage dynamic rows, client-side live financial totaling, and duplicate submission prevention.
4. **Automated Test Scenarios:** Scaffolding the 18 Django TestCase unit tests and 10 standalone debugging exercise test cases.
5. **Technical Documentation:** Generating comprehensive setup instructions and interview talking points.

---

## 3. Representative Prompts

### Prompt 1: Concurrency-Safe Order Confirmation
> *"How should I implement order confirmation in Django so that two concurrent requests for the same limited stock item cannot cause negative inventory or deadlocks? Please provide a clean function using transaction.atomic() and select_for_update()."*

### Prompt 2: All-or-Nothing CSV Import with Row Error Reporting
> *"Write a Python CSV import function for products that checks required columns, rejects duplicate product codes within the file or existing database, validates positive numbers, reports errors with row numbers, and guarantees an all-or-nothing rollback if any row fails."*

### Prompt 3: Fixing Financial Accumulator Bug in Debugging Exercise
> *"Analyze this function `def calculate_total(items): total = 0; for item in items: amount = item['qty'] * item['rate']; total = amount; return total`. Explain why it fails for multi-item lists, fix it using Python Decimal, handle edge cases (empty list, missing keys, invalid values), and provide automated tests."*

---

## 4. How Generated Code Was Reviewed and Verified

1. **Static Analysis & Django System Checks:** Every file and configuration was validated using `python manage.py check` to ensure zero model warnings and strict configuration compliance.
2. **Database Verification on Real MySQL 8.0:** All migrations were applied to a live MySQL 8.0 instance using InnoDB tables. Foreign keys, check constraints, and unique indices were verified.
3. **Automated Test Execution:** All 18 automated Django test cases were run against the live MySQL test database (`python manage.py test`) ensuring 100% pass rate.
4. **Manual End-to-End Walkthrough:** Tested browser workflows including user authentication, creating multi-item draft orders, live calculation in JavaScript, confirming orders with stock deduction, cancelling orders with stock restoration, manual stock adjustments, and CSV import.
5. **SQL Execution:** All five SQL queries in `sql_queries.sql` were executed directly against MySQL 8.0 tables to verify table names, join accuracy, and aggregate groupings.

---

## 5. Issues Identified and Corrected

During development and review, the following notable issue was identified and corrected:

- **Issue: Deadlock Hazard During Concurrent Multi-Item Order Confirmation:**
  - *Context:* When confirming two orders simultaneously that contain the same products in different orders (e.g., Order A locks Product 1 then Product 2; Order B locks Product 2 then Product 1), a relational database deadlock (`MySQL 1213: Deadlock found when trying to get lock`) could occur.
  - *Correction:* In `inventory/services.py`, product locking was updated to always sort product IDs in ascending numerical order (`product_ids = sorted([item.product_id for item in items])`) prior to executing `Product.objects.select_for_update().filter(id__in=product_ids)`. Enforcing a deterministic locking order completely prevents circular wait deadlocks across concurrent user requests.
- **Issue: Floating-Point Rounding Warnings in DRF Serializers:**
  - *Context:* DRF `DecimalField` issued user warnings when `min_value=0.0` or `max_value=20.0` were passed as Python floats.
  - *Correction:* Converted all constraint boundaries to explicit `Decimal('0.00')` and `Decimal('20.00')` objects in `sales/serializers.py`, ensuring consistent decimal precision throughout the serialization pipeline.
