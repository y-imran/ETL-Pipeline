-- Local MySQL schema for the e-commerce ETL pipeline.
-- Run once:  mysql -u root -p < scripts/schema.sql
--
-- Tables are independent: there are no FOREIGN KEY constraints.
-- The ETL process loads each table on its own.

CREATE DATABASE IF NOT EXISTS ecommerce_etl
    CHARACTER SET utf8mb4;

USE ecommerce_etl;

-- --------------------------------------------------
-- CUSTOMERS
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS raw_customers (
    customer_id   INT          NOT NULL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email         VARCHAR(255) NULL,
    city          VARCHAR(100) NULL,
    is_deleted    BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS staging_customers (
    customer_id   INT          NOT NULL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email         VARCHAR(255) NULL,
    city          VARCHAR(100) NULL,
    is_deleted    BOOLEAN      NOT NULL DEFAULT FALSE
);

-- --------------------------------------------------
-- PRODUCTS
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS raw_products (
    product_id   INT            NOT NULL PRIMARY KEY,
    product_name VARCHAR(150)   NOT NULL,
    category     VARCHAR(100)   NULL,
    price        DECIMAL(12, 2) NOT NULL,
    is_deleted   BOOLEAN        NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS staging_products (
    product_id   INT            NOT NULL PRIMARY KEY,
    product_name VARCHAR(150)   NOT NULL,
    category     VARCHAR(100)   NULL,
    price        DECIMAL(12, 2) NOT NULL,
    is_deleted   BOOLEAN        NOT NULL DEFAULT FALSE
);

-- --------------------------------------------------
-- ORDERS
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS raw_orders (
    order_id    INT          NOT NULL PRIMARY KEY,
    customer_id INT          NOT NULL,
    order_date  DATE         NOT NULL,
    status      VARCHAR(20)  NOT NULL,
    created_at  DATETIME     NOT NULL,
    updated_at  DATETIME     NOT NULL,
    is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
    INDEX idx_raw_orders_updated_at (updated_at)
);

CREATE TABLE IF NOT EXISTS staging_orders (
    order_id    INT          NOT NULL PRIMARY KEY,
    customer_id INT          NOT NULL,
    order_date  DATE         NOT NULL,
    status      VARCHAR(20)  NOT NULL,
    created_at  DATETIME     NOT NULL,
    updated_at  DATETIME     NOT NULL,
    is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
    INDEX idx_staging_orders_updated_at (updated_at)
);

-- --------------------------------------------------
-- ORDER ITEMS
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS raw_order_items (
    order_item_id INT     NOT NULL PRIMARY KEY,
    order_id      INT     NOT NULL,
    product_id    INT     NOT NULL,
    quantity      INT     NOT NULL,
    price         DECIMAL(12, 2) NOT NULL,
    is_deleted    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS staging_order_items (
    order_item_id INT     NOT NULL PRIMARY KEY,
    order_id      INT     NOT NULL,
    product_id    INT     NOT NULL,
    quantity      INT     NOT NULL,
    price         DECIMAL(12, 2) NOT NULL,
    total_price   DECIMAL(12, 2) NULL,
    is_deleted    BOOLEAN NOT NULL DEFAULT FALSE
);

-- --------------------------------------------------
-- INCREMENTAL LOAD WATERMARK
-- --------------------------------------------------

CREATE TABLE IF NOT EXISTS etl_watermarks (
    pipeline_name  VARCHAR(100) NOT NULL PRIMARY KEY,
    last_watermark DATETIME     NOT NULL
);

-- The first run should load every order, so seed the bookmark with 1970.
INSERT INTO etl_watermarks (pipeline_name, last_watermark)
VALUES ('orders', '1970-01-01 00:00:00')
ON DUPLICATE KEY UPDATE last_watermark = last_watermark;
