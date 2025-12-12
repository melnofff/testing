-- Disaster Recovery Testing SQL Scripts
-- Tests backup, restore, and recovery procedures

-- ============================================================================
-- SCENARIO 1: Full Database Backup and Restore
-- ============================================================================

-- Create test database
CREATE DATABASE IF NOT EXISTS test_dr_database;
USE test_dr_database;

-- Create test tables
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_email (email)
);

CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    order_number VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'completed', 'cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_order_number (order_number)
);

-- Insert test data
INSERT INTO users (username, email) VALUES
    ('user1', 'user1@example.com'),
    ('user2', 'user2@example.com'),
    ('user3', 'user3@example.com'),
    ('user4', 'user4@example.com'),
    ('user5', 'user5@example.com');

INSERT INTO orders (user_id, order_number, total_amount, status) VALUES
    (1, 'ORD001', 100.50, 'completed'),
    (1, 'ORD002', 250.00, 'pending'),
    (2, 'ORD003', 75.25, 'completed'),
    (3, 'ORD004', 500.00, 'pending'),
    (4, 'ORD005', 150.75, 'cancelled');

-- Create checksum for data integrity verification
CREATE TABLE IF NOT EXISTS data_checksums (
    table_name VARCHAR(50) PRIMARY KEY,
    record_count INT NOT NULL,
    checksum_value VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Calculate and store checksums
INSERT INTO data_checksums (table_name, record_count, checksum_value)
SELECT
    'users' as table_name,
    COUNT(*) as record_count,
    MD5(GROUP_CONCAT(CONCAT(id, username, email) ORDER BY id)) as checksum_value
FROM users;

INSERT INTO data_checksums (table_name, record_count, checksum_value)
SELECT
    'orders' as table_name,
    COUNT(*) as record_count,
    MD5(GROUP_CONCAT(CONCAT(id, order_number, total_amount) ORDER BY id)) as checksum_value
FROM orders;

-- ============================================================================
-- BACKUP PROCEDURES
-- ============================================================================

-- Full backup simulation
-- In practice, use: mysqldump -u root -p test_dr_database > backup_full.sql

-- Point-in-time backup marker
CREATE TABLE IF NOT EXISTS backup_points (
    id INT PRIMARY KEY AUTO_INCREMENT,
    backup_name VARCHAR(100) NOT NULL,
    backup_type ENUM('full', 'incremental', 'differential') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INT,
    file_size_mb DECIMAL(10, 2)
);

INSERT INTO backup_points (backup_name, backup_type, record_count, file_size_mb)
VALUES ('backup_full_20251210', 'full', 10, 1.5);

-- ============================================================================
-- SCENARIO 2: Point-in-Time Recovery (PITR)
-- ============================================================================

-- Mark point-in-time for recovery
SET @recovery_point = NOW();

-- Simulate some transactions after backup
INSERT INTO users (username, email) VALUES
    ('user6', 'user6@example.com'),
    ('user7', 'user7@example.com');

INSERT INTO orders (user_id, order_number, total_amount, status) VALUES
    (5, 'ORD006', 300.00, 'pending');

-- Create transaction log marker
CREATE TABLE IF NOT EXISTS transaction_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    operation VARCHAR(20) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO transaction_log (operation, table_name, record_id) VALUES
    ('INSERT', 'users', 6),
    ('INSERT', 'users', 7),
    ('INSERT', 'orders', 6);

-- Verify PITR capability
SELECT
    'Recovery Point' as info_type,
    @recovery_point as recovery_time,
    COUNT(*) as records_after_point
FROM transaction_log
WHERE created_at > @recovery_point;

-- ============================================================================
-- SCENARIO 3: Data Corruption Simulation and Recovery
-- ============================================================================

-- Backup current state
DROP TABLE IF EXISTS users_backup;
DROP TABLE IF EXISTS orders_backup;
CREATE TABLE users_backup AS SELECT * FROM users;
CREATE TABLE orders_backup AS SELECT * FROM orders;

-- Remove UNIQUE constraint temporarily for corruption simulation
ALTER TABLE users DROP INDEX unique_email;

-- Simulate data corruption
UPDATE users SET email = 'corrupted@example.com' WHERE id IN (1, 2, 3);
UPDATE orders SET total_amount = 0.00 WHERE id IN (1, 2);

-- Detect corruption
SELECT
    'CORRUPTION DETECTED' as alert,
    COUNT(*) as affected_users
FROM users
WHERE email = 'corrupted@example.com';

SELECT
    'CORRUPTION DETECTED' as alert,
    COUNT(*) as affected_orders
FROM orders
WHERE total_amount = 0.00 AND status != 'cancelled';

-- Restore from backup
UPDATE users u
JOIN users_backup ub ON u.id = ub.id
SET u.email = ub.email
WHERE u.email = 'corrupted@example.com';

UPDATE orders o
JOIN orders_backup ob ON o.id = ob.id
SET o.total_amount = ob.total_amount
WHERE o.total_amount = 0.00 AND o.status != 'cancelled';

-- Restore UNIQUE constraint
ALTER TABLE users ADD UNIQUE KEY unique_email (email);

-- Verify restoration
SELECT
    'users' as table_name,
    COUNT(*) as record_count,
    MD5(GROUP_CONCAT(CONCAT(id, username, email) ORDER BY id)) as current_checksum,
    (SELECT checksum_value FROM data_checksums WHERE table_name = 'users') as original_checksum,
    CASE
        WHEN MD5(GROUP_CONCAT(CONCAT(id, username, email) ORDER BY id)) =
             (SELECT checksum_value FROM data_checksums WHERE table_name = 'users')
        THEN 'MATCH'
        ELSE 'MISMATCH'
    END as integrity_status
FROM users;

-- ============================================================================
-- SCENARIO 4: Transaction Rollback Testing
-- ============================================================================

-- Start transaction
START TRANSACTION;

-- Make changes
INSERT INTO users (username, email) VALUES ('temp_user', 'temp@example.com');
SET @temp_user_id = LAST_INSERT_ID();

INSERT INTO orders (user_id, order_number, total_amount) VALUES
    (@temp_user_id, 'TEMP001', 999.99);

-- Simulate failure and rollback
ROLLBACK;

-- Verify rollback
SELECT
    'Transaction Rollback Test' as test_name,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS - Data properly rolled back'
        ELSE 'FAIL - Data not rolled back'
    END as result
FROM users
WHERE username = 'temp_user';

-- ============================================================================
-- RTO/RPO Metrics Calculation
-- ============================================================================

CREATE TABLE IF NOT EXISTS recovery_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    test_scenario VARCHAR(100) NOT NULL,
    failure_time TIMESTAMP NOT NULL,
    recovery_start TIMESTAMP NOT NULL,
    recovery_complete TIMESTAMP NOT NULL,
    rto_seconds INT NOT NULL,
    rpo_seconds INT NOT NULL,
    data_loss_records INT DEFAULT 0,
    test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample RTO/RPO data
INSERT INTO recovery_metrics
(test_scenario, failure_time, recovery_start, recovery_complete, rto_seconds, rpo_seconds, data_loss_records)
VALUES
    ('Full Database Restore', '2025-12-10 10:00:00', '2025-12-10 10:01:00', '2025-12-10 10:15:00', 840, 3600, 0),
    ('Point-in-Time Recovery', '2025-12-10 11:00:00', '2025-12-10 11:02:00', '2025-12-10 11:10:00', 480, 300, 2),
    ('Data Corruption Recovery', '2025-12-10 12:00:00', '2025-12-10 12:00:30', '2025-12-10 12:05:00', 270, 0, 0),
    ('Transaction Rollback', '2025-12-10 13:00:00', '2025-12-10 13:00:01', '2025-12-10 13:00:02', 1, 0, 0);

-- Calculate average RTO and RPO
SELECT
    'Recovery Metrics Summary' as report_type,
    COUNT(*) as total_tests,
    ROUND(AVG(rto_seconds), 2) as avg_rto_seconds,
    ROUND(AVG(rpo_seconds), 2) as avg_rpo_seconds,
    MAX(rto_seconds) as max_rto_seconds,
    MAX(rpo_seconds) as max_rpo_seconds,
    SUM(data_loss_records) as total_data_loss
FROM recovery_metrics;

-- Detailed breakdown
SELECT
    test_scenario,
    CONCAT(FLOOR(rto_seconds / 60), 'm ', MOD(rto_seconds, 60), 's') as rto_formatted,
    CONCAT(FLOOR(rpo_seconds / 60), 'm ', MOD(rpo_seconds, 60), 's') as rpo_formatted,
    data_loss_records,
    CASE
        WHEN rto_seconds <= 300 THEN 'Excellent (<=5 min)'
        WHEN rto_seconds <= 900 THEN 'Good (<=15 min)'
        WHEN rto_seconds <= 3600 THEN 'Acceptable (<=1 hour)'
        ELSE 'Needs Improvement (>1 hour)'
    END as rto_rating
FROM recovery_metrics
ORDER BY test_date DESC;

-- ============================================================================
-- CLEANUP (for testing purposes)
-- ============================================================================

-- DROP TABLE IF EXISTS users_backup;
-- DROP TABLE IF EXISTS orders_backup;
-- DROP DATABASE IF EXISTS test_dr_database;

-- ============================================================================
-- RECOMMENDATIONS
-- ============================================================================

SELECT '
DISASTER RECOVERY RECOMMENDATIONS:

1. RTO (Recovery Time Objective) Analysis:
   - Target: < 15 minutes for critical systems
   - Current Average: 398 seconds (~6.6 minutes) [OK] MEETS TARGET
   - Max RTO: 840 seconds (14 minutes) [OK] ACCEPTABLE

2. RPO (Recovery Point Objective) Analysis:
   - Target: < 1 hour for most scenarios
   - Current Average: 975 seconds (~16 minutes) [OK] MEETS TARGET
   - Recommend: Implement binary logging for near-zero RPO

3. Backup Strategy:
   - Implement automated daily full backups
   - Hourly incremental backups for critical data
   - Test restore procedures monthly
   - Store backups in geographically separate location

4. Data Integrity:
   - Implement checksum validation for all backups
   - Use ACID-compliant transactions
   - Regular integrity checks (weekly)
   - Automated corruption detection

5. High Availability:
   - Consider database replication (Master-Slave)
   - Implement automatic failover mechanism
   - Use connection pooling for resilience
   - Geographic redundancy for critical services

6. Monitoring:
   - Set up alerts for backup failures
   - Monitor disk space for backup storage
   - Track RTO/RPO metrics continuously
   - Automated recovery testing

7. Documentation:
   - Maintain runbook for recovery procedures
   - Document all backup schedules
   - Regular disaster recovery drills
   - Keep contact list for emergency response

' as recommendations;
