-- Migration script to change INTEGER to BIGINT for Telegram IDs
-- Run this script directly on your PostgreSQL database if migrations are not working

-- 1. Users table
ALTER TABLE Users ALTER COLUMN TelegramID TYPE BIGINT;

-- 2. Sellers table
ALTER TABLE Sellers ALTER COLUMN TelegramID TYPE BIGINT;

-- 3. CreditCustomers table
ALTER TABLE CreditCustomers ALTER COLUMN TelegramID TYPE BIGINT;

-- 4. Orders table
ALTER TABLE Orders ALTER COLUMN BuyerID TYPE BIGINT;

-- 5. Carts table
ALTER TABLE Carts ALTER COLUMN UserID TYPE BIGINT;

-- Verify the changes
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE column_name IN ('TelegramID', 'BuyerID', 'UserID')
    AND table_name IN ('users', 'sellers', 'creditcustomers', 'orders', 'carts')
ORDER BY table_name, column_name;
