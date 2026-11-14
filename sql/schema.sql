-- E-commerce data model. Running this file recreates the four tables.
-- Drop child tables first, create parent tables first.
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    title        VARCHAR(300) NOT NULL,
    category     VARCHAR(100) NOT NULL,
    price        NUMERIC(10,2) NOT NULL CHECK (price > 0),
    description  TEXT,
    rating_rate  NUMERIC(3,2) CHECK (rating_rate BETWEEN 0 AND 5),
    rating_count INTEGER CHECK (rating_count >= 0)
);

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL UNIQUE,
    city        VARCHAR(100)
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date  DATE NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

-- Bridge table: one order has many products, one product is in many orders.
CREATE TABLE order_items (
    order_id   INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

-- PostgreSQL does not create an index for a foreign key automatically.
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_order_items_product ON order_items (product_id);
