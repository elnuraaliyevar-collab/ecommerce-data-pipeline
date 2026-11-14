-- Query 1: total sales value by product (main demo query)
SELECT p.product_id,
       p.title,
       SUM(oi.quantity) AS units_sold,
       SUM(oi.quantity * oi.unit_price) AS total_sales
FROM order_items AS oi
JOIN products AS p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.title
ORDER BY total_sales DESC;

-- Query 2: total sales value by product category
SELECT p.category,
       SUM(oi.quantity * oi.unit_price) AS total_sales
FROM order_items AS oi
JOIN products AS p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY total_sales DESC;

-- Query 3: total sales value by customer city
SELECT c.city,
       COUNT(DISTINCT o.order_id) AS orders,
       SUM(oi.quantity * oi.unit_price) AS total_sales
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
JOIN order_items AS oi ON oi.order_id = o.order_id
GROUP BY c.city
ORDER BY total_sales DESC;

-- Query 4: value of every order
SELECT o.order_id,
       c.full_name,
       o.order_date,
       SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
JOIN order_items AS oi ON oi.order_id = o.order_id
GROUP BY o.order_id, c.full_name, o.order_date
ORDER BY o.order_id;
