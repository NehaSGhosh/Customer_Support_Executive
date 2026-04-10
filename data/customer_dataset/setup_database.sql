-- ============================================================
-- customer_support database setup + CSV load script for PostgreSQL
-- ============================================================
-- HOW TO RUN
-- 1) Open psql as a superuser or a user that can create databases:
--      psql -U postgres -f setup_database.sql \
--           -v customers_path='C:/path/to/customers_clean.csv' \
--           -v orders_path='C:/path/to/orders_clean.csv' \
--           -v tickets_path='C:/path/to/support_tickets_clean.csv'
--
-- 2) Use forward slashes in Windows paths.
-- 3) This script uses psql meta-commands like \copy and \connect.
--
-- WHAT THIS SCRIPT DOES
-- - Creates database: customer_support
-- - Creates staging tables for safe CSV import
-- - Loads the CSV files
-- - Creates final typed tables
-- - Inserts/casts data safely
-- - Adds primary keys, foreign keys, and indexes
-- - Prints row counts at the end
-- ============================================================

\set ON_ERROR_STOP on

-- =========================
-- VALIDATE FILE PATHS
-- =========================

\if :{?customers_path}
\else
  \echo ERROR: customers_path not provided
  \quit
\endif

\if :{?orders_path}
\else
  \echo ERROR: orders_path not provided
  \quit
\endif

\if :{?tickets_path}
\else
  \echo ERROR: tickets_path not provided
  \quit
\endif

-- ---- Create database if it does not already exist ----
DROP DATABASE IF EXISTS customer_support;
CREATE DATABASE customer_support;
\connect customer_support;

SET client_min_messages TO WARNING;
SET datestyle TO ISO, YMD;

-- ============================================================
-- 1) STAGING TABLES (all text so CSV load is forgiving)
-- ============================================================
DROP TABLE IF EXISTS stg_customers;
CREATE TABLE stg_customers (
    customer_id     TEXT,
    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,
    phone_number    TEXT,
    gender          TEXT,
    dob             TEXT,
    signup_date     TEXT,
    address         TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    "device_id(s)" TEXT,
    source          TEXT
);

DROP TABLE IF EXISTS stg_orders;
CREATE TABLE stg_orders (
    order_id         TEXT,
    customer_id      TEXT,
    product_id       TEXT,
    order_amount     TEXT,
    order_date       TEXT,
    payment_method   TEXT,
    status           TEXT,
    quantity         TEXT
);

DROP TABLE IF EXISTS stg_support_tickets;
CREATE TABLE stg_support_tickets (
    ticket_id               TEXT,
    customer_id             TEXT,
    issue_type              TEXT,
    ticket_created          TEXT,
    ticket_resolved         TEXT,
    resolution_time_hours   TEXT,
    sentiment               TEXT,
    support_agent           TEXT
);

-- ============================================================
-- 2) LOAD CSV FILES INTO STAGING TABLES
-- ============================================================
\echo Loading customers from :customers_path
COPY stg_customers
FROM :'customers_path'
WITH (FORMAT csv, HEADER true);

\echo Loading orders from :orders_path
COPY stg_orders
FROM :'orders_path'
WITH (FORMAT csv, HEADER true);

\echo Loading support tickets from :tickets_path
COPY stg_support_tickets
FROM :'tickets_path'
WITH (FORMAT csv, HEADER true);

-- ============================================================
-- 3) FINAL TABLES
-- ============================================================
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id     UUID PRIMARY KEY,
    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,
    phone_number    TEXT,
    gender          TEXT,
    dob             DATE,
    signup_date     DATE,
    address         TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    device_ids      TEXT,
    source          TEXT
);

CREATE TABLE orders (
    order_id         UUID PRIMARY KEY,
    customer_id      UUID NOT NULL,
    product_id       TEXT,
    order_amount     NUMERIC(12,2),
    order_date       DATE,
    payment_method   TEXT,
    status           TEXT,
    quantity         INTEGER,
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE support_tickets (
    ticket_id               UUID PRIMARY KEY,
    customer_id             UUID NOT NULL,
    issue_type              TEXT,
    ticket_created          TIMESTAMP,
    ticket_resolved         TIMESTAMP,
    resolution_time_hours   NUMERIC(10,2),
    sentiment               TEXT,
    support_agent           TEXT,
    CONSTRAINT fk_tickets_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- ============================================================
-- 4) INSERT TYPED DATA
-- ============================================================
INSERT INTO customers (
    customer_id,
    first_name,
    last_name,
    email,
    phone_number,
    gender,
    dob,
    signup_date,
    address,
    city,
    state,
    country,
    device_ids,
    source
)
SELECT
    NULLIF(TRIM(customer_id), '')::UUID,
    NULLIF(TRIM(first_name), ''),
    NULLIF(TRIM(last_name), ''),
    NULLIF(TRIM(email), ''),
    NULLIF(TRIM(phone_number), ''),
    NULLIF(TRIM(gender), ''),
    NULLIF(TRIM(dob), '')::DATE,
    NULLIF(TRIM(signup_date), '')::DATE,
    NULLIF(TRIM(address), ''),
    NULLIF(TRIM(city), ''),
    NULLIF(TRIM(state), ''),
    NULLIF(TRIM(country), ''),
    NULLIF(TRIM("device_id(s)"), ''),
    NULLIF(TRIM(source), '')
FROM stg_customers;

INSERT INTO orders (
    order_id,
    customer_id,
    product_id,
    order_amount,
    order_date,
    payment_method,
    status,
    quantity
)
SELECT
    NULLIF(TRIM(order_id), '')::UUID,
    NULLIF(TRIM(customer_id), '')::UUID,
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(order_amount), '')::NUMERIC(12,2),
    TO_DATE(NULLIF(TRIM(order_date), ''), 'MM/DD/YYYY'),
    NULLIF(TRIM(payment_method), ''),
    NULLIF(TRIM(status), ''),
    NULLIF(TRIM(quantity), '')::INTEGER
FROM stg_orders;

INSERT INTO support_tickets (
    ticket_id,
    customer_id,
    issue_type,
    ticket_created,
    ticket_resolved,
    resolution_time_hours,
    sentiment,
    support_agent
)
SELECT
    NULLIF(TRIM(ticket_id), '')::UUID,
    NULLIF(TRIM(customer_id), '')::UUID,
    NULLIF(TRIM(issue_type), ''),
    NULLIF(TRIM(ticket_created), '')::TIMESTAMP,
    NULLIF(TRIM(ticket_resolved), '')::TIMESTAMP,
    NULLIF(TRIM(resolution_time_hours), '')::NUMERIC(10,2),
    NULLIF(TRIM(sentiment), ''),
    NULLIF(TRIM(support_agent), '')
FROM stg_support_tickets;

-- ============================================================
-- 5) OPTIONAL PERFORMANCE INDEXES
-- ============================================================
CREATE INDEX idx_customers_email              ON customers(email);
CREATE INDEX idx_customers_signup_date        ON customers(signup_date);
CREATE INDEX idx_orders_customer_id           ON orders(customer_id);
CREATE INDEX idx_orders_order_date            ON orders(order_date);
CREATE INDEX idx_orders_status                ON orders(status);
CREATE INDEX idx_support_tickets_customer_id  ON support_tickets(customer_id);
CREATE INDEX idx_support_tickets_issue_type   ON support_tickets(issue_type);
CREATE INDEX idx_support_tickets_created      ON support_tickets(ticket_created);

-- ============================================================
-- 6) VALIDATION OUTPUT
-- ============================================================
\echo ============================================================
\echo Load complete. Row counts:
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'support_tickets', COUNT(*) FROM support_tickets
ORDER BY table_name;

\echo ============================================================
\echo Null checks:
SELECT 'orders.order_date is null' AS check_name, COUNT(*) AS issue_count
FROM orders WHERE order_date IS NULL
UNION ALL
SELECT 'support_tickets.ticket_created is null', COUNT(*)
FROM support_tickets WHERE ticket_created IS NULL
ORDER BY check_name;

-- =========================
-- 7) CLEANUP STAGING TABLES
-- =========================
DROP TABLE IF EXISTS staging_customers;
DROP TABLE IF EXISTS staging_orders;
DROP TABLE IF EXISTS staging_tickets;

\echo ============================================================
\echo Database setup finished successfully.
