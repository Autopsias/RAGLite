-- Test data for database integration tests
-- Populates financial_tables with proper time-series data for forecasting tests

-- Clean existing test data first
DELETE FROM financial_tables WHERE metric LIKE 'test_%';

-- Insert revenue/turnover data with proper Mon-YY periods
INSERT INTO financial_tables (document_id, page_number, table_index, entity, metric, period, fiscal_year, value, unit, section_type) VALUES
-- Revenue data (turnover metric for revenue queries)
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Jan-24', 2024, 100.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Feb-24', 2024, 105.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Mar-24', 2024, 110.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Apr-24', 2024, 115.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'May-24', 2024, 120.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Jun-24', 2024, 125.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Jul-24', 2024, 130.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Aug-24', 2024, 135.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Sep-24', 2024, 140.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Oct-24', 2024, 145.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Nov-24', 2024, 150.0, 'M EUR', 'Table'),
('test_doc_1', 1, 1, 'Test Company', 'turnover', 'Dec-24', 2024, 155.0, 'M EUR', 'Table'),

-- EBITDA data (EBITDA IFRS metric for ebitda queries)
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Jan-24', 2024, 25.0, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Feb-24', 2024, 26.5, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Mar-24', 2024, 28.0, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Apr-24', 2024, 29.5, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'May-24', 2024, 31.0, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Jun-24', 2024, 32.5, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Jul-24', 2024, 34.0, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Aug-24', 2024, 35.5, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Sep-24', 2024, 37.0, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Oct-24', 2024, 38.5, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Nov-24', 2024, 40.0, 'M EUR', 'Table'),
('test_doc_2', 1, 1, 'Group', 'EBITDA IFRS', 'Dec-24', 2024, 41.5, 'M EUR', 'Table'),

-- Expenses data
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Jan-24', 2024, 80.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Feb-24', 2024, 82.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Mar-24', 2024, 84.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Apr-24', 2024, 86.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'May-24', 2024, 88.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Jun-24', 2024, 90.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Jul-24', 2024, 92.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Aug-24', 2024, 94.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Sep-24', 2024, 96.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Oct-24', 2024, 98.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Nov-24', 2024, 100.0, 'M EUR', 'Table'),
('test_doc_3', 1, 1, 'Test Company', 'test_expenses', 'Dec-24', 2024, 102.0, 'M EUR', 'Table'),

-- Cash flow data
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Jan-24', 2024, 15.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Feb-24', 2024, 16.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Mar-24', 2024, 17.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Apr-24', 2024, 18.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'May-24', 2024, 19.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Jun-24', 2024, 20.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Jul-24', 2024, 21.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Aug-24', 2024, 22.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Sep-24', 2024, 23.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Oct-24', 2024, 24.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Nov-24', 2024, 25.0, 'M EUR', 'Table'),
('test_doc_4', 1, 1, 'Test Company', 'test_cash_flow', 'Dec-24', 2024, 26.0, 'M EUR', 'Table');
