-- Use the database
USE documate;

-- Add username column to users table if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255) NOT NULL DEFAULT '';

-- Ensure other columns exist in users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NOT NULL DEFAULT '';

-- Add missing columns to other tables if needed
-- For family_members
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS user_id INT NOT NULL DEFAULT 0;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS name VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS relation VARCHAR(255) DEFAULT NULL;

-- Add foreign key if not exists (this might fail if data issues, but try)
ALTER TABLE family_members ADD CONSTRAINT fk_family_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- For documents
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id INT NOT NULL DEFAULT 0;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS member_id INT DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS title VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS description TEXT DEFAULT NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS filename VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS expiry_date DATE DEFAULT NULL;

-- Foreign keys for documents
ALTER TABLE documents ADD CONSTRAINT fk_doc_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE documents ADD CONSTRAINT fk_doc_member FOREIGN KEY (member_id) REFERENCES family_members(id) ON DELETE SET NULL;

-- For reminders
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS document_id INT NOT NULL DEFAULT 0;
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS reminder_date DATE NOT NULL DEFAULT '1970-01-01';
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS reminder_type VARCHAR(50) NOT NULL DEFAULT '';
ALTER TABLE reminders ADD COLUMN IF NOT EXISTS sent_flag TINYINT DEFAULT 0;

ALTER TABLE reminders ADD CONSTRAINT fk_rem_doc FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;

-- For user_notification_preferences
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS notify_30_days TINYINT DEFAULT 1;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS notify_7_days TINYINT DEFAULT 1;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS notify_1_day TINYINT DEFAULT 1;
ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS notify_day_of TINYINT DEFAULT 1;

ALTER TABLE user_notification_preferences ADD CONSTRAINT fk_prefs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
