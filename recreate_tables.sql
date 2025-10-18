-- Use the database
USE documate;

-- Drop tables in reverse order to avoid foreign key issues
DROP TABLE IF EXISTS reminders;
DROP TABLE IF EXISTS user_notification_preferences;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS family_members;
DROP TABLE IF EXISTS otp_verifications;
DROP TABLE IF EXISTS users;

-- Create users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- Create family_members table
CREATE TABLE family_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    relation VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create documents table
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    member_id INT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    expiry_date DATE NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES family_members(id) ON DELETE SET NULL
);

-- Create reminders table
CREATE TABLE reminders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    reminder_date DATE NOT NULL,
    reminder_type VARCHAR(50) NOT NULL,
    sent_flag TINYINT DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Create otp_verifications table
CREATE TABLE otp_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    otp VARCHAR(6) NOT NULL,
    expiry DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create user_notification_preferences table
CREATE TABLE user_notification_preferences (
    user_id INT PRIMARY KEY,
    notify_30_days TINYINT DEFAULT 1,
    notify_7_days TINYINT DEFAULT 1,
    notify_1_day TINYINT DEFAULT 1,
    notify_day_of TINYINT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Verify tables created
SHOW TABLES;
DESCRIBE users;
DESCRIBE family_members;
DESCRIBE documents;
DESCRIBE reminders;
DESCRIBE otp_verifications;
DESCRIBE user_notification_preferences;
