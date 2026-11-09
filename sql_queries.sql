-- =============================================================================
-- Savyant Systems Technical Assignment: SQL Queries
-- Database Engine: MySQL 8.0 (InnoDB)
--
-- This script contains the 5 standalone SQL queries requested in the assignment,
-- using the exact table and column names from the Django ORM schema.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Top 3 customers by confirmed order grand total
-- -----------------------------------------------------------------------------
-- Explanation:
-- Joins masters_customer with sales_salesorder on customer_id, filters exclusively
-- for orders with status = 'CONFIRMED', groups by customer, sums grand_total,
-- and orders in descending order to return the top 3 revenue-generating customers.

SELECT 
    c.id AS customer_id,
    c.name AS customer_name,
    c.city,
    COUNT(so.id) AS confirmed_orders_count,
    ROUND(SUM(so.grand_total), 2) AS total_sales_amount
FROM masters_customer c
INNER JOIN sales_salesorder so 
    ON c.id = so.customer_id
WHERE so.status = 'CONFIRMED'
GROUP BY c.id, c.name, c.city
ORDER BY total_sales_amount DESC
LIMIT 3;


-- -----------------------------------------------------------------------------
-- 2. Top 3 products by quantity sold in confirmed orders
-- -----------------------------------------------------------------------------
-- Explanation:
-- Joins masters_product with sales_salesorderitem and sales_salesorder.
-- Filters for CONFIRMED orders so draft and cancelled orders are excluded.
-- Aggregates total quantity sold per product and sorts descending to return the top 3.

SELECT 
    p.id AS product_id,
    p.code AS product_code,
    p.name AS product_name,
    p.category,
    SUM(soi.quantity) AS total_quantity_sold,
    ROUND(SUM(soi.amount), 2) AS gross_sales_value
FROM masters_product p
INNER JOIN sales_salesorderitem soi 
    ON p.id = soi.product_id
INNER JOIN sales_salesorder so 
    ON soi.order_id = so.id
WHERE so.status = 'CONFIRMED'
GROUP BY p.id, p.code, p.name, p.category
ORDER BY total_quantity_sold DESC
LIMIT 3;


-- -----------------------------------------------------------------------------
-- 3. Customers who have never placed any order
-- -----------------------------------------------------------------------------
-- Explanation:
-- Performs a LEFT JOIN from masters_customer to sales_salesorder.
-- Customers without any sales order records will have NULL for all sales_salesorder
-- columns. Filtering by WHERE so.id IS NULL identifies all such zero-order customers.

SELECT 
    c.id AS customer_id,
    c.name AS customer_name,
    c.email,
    c.mobile,
    c.city,
    c.status
FROM masters_customer c
LEFT JOIN sales_salesorder so 
    ON c.id = so.customer_id
WHERE so.id IS NULL
ORDER BY c.name ASC;


-- -----------------------------------------------------------------------------
-- 4. Month-wise confirmed sales grouped by year and month
-- -----------------------------------------------------------------------------
-- Explanation:
-- Groups confirmed sales orders by YEAR(order_date) and MONTH(order_date).
-- Computes the order count, total subtotal, total discounts, and grand sales revenue.
-- Orders chronologically in descending order to review recent performance first.

SELECT 
    YEAR(so.order_date) AS sales_year,
    MONTH(so.order_date) AS sales_month,
    DATE_FORMAT(so.order_date, '%M %Y') AS month_name,
    COUNT(so.id) AS confirmed_orders_count,
    ROUND(SUM(so.subtotal), 2) AS total_subtotal,
    ROUND(SUM(so.discount_amount), 2) AS total_discounts,
    ROUND(SUM(so.grand_total), 2) AS total_grand_sales
FROM sales_salesorder so
WHERE so.status = 'CONFIRMED'
GROUP BY YEAR(so.order_date), MONTH(so.order_date), DATE_FORMAT(so.order_date, '%M %Y')
ORDER BY sales_year DESC, sales_month DESC;


-- -----------------------------------------------------------------------------
-- 5. Products below a given stock threshold (e.g. threshold = 10)
-- -----------------------------------------------------------------------------
-- Explanation:
-- Filters products whose current stock_quantity is less than or equal to a given
-- threshold (e.g., 10 units), ordered from lowest stock to highest stock.

SELECT 
    p.id AS product_id,
    p.code AS product_code,
    p.name AS product_name,
    p.category,
    p.price,
    p.stock_quantity,
    p.status
FROM masters_product p
WHERE p.stock_quantity <= 10
ORDER BY p.stock_quantity ASC, p.name ASC;
