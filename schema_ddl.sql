-- DDL Script for IBKR WHT Database Schema
-- Database: ibkr_wht
-- Tables: transactions, dividend_report

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS ibkr_wht 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE ibkr_wht;

-- Table to store raw transactions from IBKR CSV statements
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_type VARCHAR(50) NOT NULL COMMENT 'Transaction type: Dividends or Withholding Tax',
    currency VARCHAR(10) NOT NULL COMMENT 'Currency code (e.g., USD)',
    date DATE NOT NULL COMMENT 'Transaction date',
    ticker VARCHAR(20) NOT NULL COMMENT 'Stock ticker symbol',
    detail VARCHAR(255) COMMENT 'Original transaction description',
    amount DECIMAL(15, 4) NOT NULL COMMENT 'Transaction amount (negative for tax, positive for refunds/dividends)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_item_type (item_type),
    INDEX idx_ticker (ticker),
    INDEX idx_date (date),
    INDEX idx_currency (currency),
    INDEX idx_ticker_item_type (ticker, item_type),
    UNIQUE KEY uq_transaction (item_type, currency, date, ticker, amount)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Stores raw dividend and withholding tax transactions from IBKR statements';

-- Table to store generated dividend and WHT reports
CREATE TABLE IF NOT EXISTS dividend_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL COMMENT 'Date when the report was generated',
    ticker VARCHAR(20) NOT NULL COMMENT 'Stock ticker symbol',
    total_dividends DECIMAL(15, 4) NOT NULL DEFAULT 0 COMMENT 'Total dividend amount',
    total_wht_paid DECIMAL(15, 4) NOT NULL DEFAULT 0 COMMENT 'Total withholding tax paid (absolute value)',
    total_wht_refunded DECIMAL(15, 4) NOT NULL DEFAULT 0 COMMENT 'Total withholding tax refunded',
    net_wht DECIMAL(15, 4) NOT NULL DEFAULT 0 COMMENT 'Net WHT (Paid - Refunded)',
    final_amount DECIMAL(15, 4) NOT NULL DEFAULT 0 COMMENT 'Final amount after tax (Dividends - Net WHT)',
    wht_refund_pct DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT 'WHT refund percentage',
    final_amount_pct DECIMAL(5, 2) NOT NULL DEFAULT 0 COMMENT 'Final amount as percentage of dividends',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_report_date (report_date),
    INDEX idx_ticker (ticker)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Stores aggregated dividend and WHT reports per ticker';

-- Migration: add unique constraint to existing tables (run if table already exists)
-- ALTER TABLE transactions ADD UNIQUE KEY uq_transaction (item_type, currency, date, ticker, amount);

-- Sample queries for reference:
-- Get all USD withholding tax transactions:
-- SELECT * FROM transactions WHERE currency = 'USD' AND item_type = 'Withholding Tax';

-- Get dividend summary by ticker:
-- SELECT ticker, SUM(amount) as total_dividends 
-- FROM transactions 
-- WHERE item_type = 'Dividends' AND currency = 'USD'
-- GROUP BY ticker;

-- Get WHT paid by ticker (negative amounts):
-- SELECT ticker, ABS(SUM(amount)) as total_wht_paid
-- FROM transactions 
-- WHERE item_type = 'Withholding Tax' AND currency = 'USD' AND amount < 0
-- GROUP BY ticker;

-- Get WHT refunded by ticker (positive amounts):
-- SELECT ticker, SUM(amount) as total_wht_refunded
-- FROM transactions 
-- WHERE item_type = 'Withholding Tax' AND currency = 'USD' AND amount > 0
-- GROUP BY ticker;
