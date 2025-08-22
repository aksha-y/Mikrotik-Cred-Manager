#!/usr/bin/env python3
"""
Database initialization script for MikroTik Credential Manager
"""

import mysql.connector
from mysql.connector import Error
import hashlib
import secrets
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'mikrotik_cred_manager')
}

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect without specifying database
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        
        cursor = connection.cursor()
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        print(f"✓ Database '{DB_CONFIG['database']}' created or already exists")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"✗ Error creating database: {e}")
        return False
    
    return True

def create_tables():
    """Create all required tables"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin', 'full_access', 'write_access', 'read_only') DEFAULT 'read_only',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                INDEX idx_username (username),
                INDEX idx_email (email),
                INDEX idx_role (role),
                INDEX idx_active (is_active)
            )
        """)
        print("✓ Users table created")
        
        # Credential requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credential_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                wan_ip VARCHAR(15) NOT NULL,
                temp_username VARCHAR(50) NOT NULL,
                temp_password VARCHAR(50) NOT NULL,
                purpose TEXT NOT NULL,
                duration_minutes INT NOT NULL,
                status ENUM('active', 'expired', 'revoked') DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                revoked_at TIMESTAMP NULL,
                revoked_by INT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (revoked_by) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_wan_ip (wan_ip),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at),
                INDEX idx_expires_at (expires_at),
                INDEX idx_temp_username (temp_username)
            )
        """)
        print("✓ Credential requests table created")
        
        # Activity logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                action VARCHAR(50) NOT NULL,
                target_ip VARCHAR(15) NULL,
                details TEXT NULL,
                ip_address VARCHAR(45) NULL,
                user_agent TEXT NULL,
                status ENUM('success', 'failed', 'error') DEFAULT 'success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_user_id (user_id),
                INDEX idx_action (action),
                INDEX idx_target_ip (target_ip),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            )
        """)
        print("✓ Activity logs table created")
        
        # System settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT NULL,
                description TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_setting_key (setting_key)
            )
        """)
        print("✓ System settings table created")
        
        connection.commit()
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"✗ Error creating tables: {e}")
        return False
    
    return True

def create_admin_user():
    """Create default admin user"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Check if admin user already exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if cursor.fetchone():
            print("✓ Admin user already exists")
            cursor.close()
            connection.close()
            return True
        
        # Generate admin password
        admin_password = secrets.token_urlsafe(12)
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        
        # Insert admin user
        cursor.execute("""
            INSERT INTO users (username, email, full_name, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            'admin',
            'admin@company.com',
            'System Administrator',
            password_hash,
            'admin',
            True
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("✓ Admin user created successfully")
        print(f"  Username: admin")
        print(f"  Password: {admin_password}")
        print("  ⚠️  Please save this password and change it after first login!")
        
        return True
        
    except Error as e:
        print(f"✗ Error creating admin user: {e}")
        return False

def insert_default_settings():
    """Insert default system settings"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        default_settings = [
            ('mikrotik_service_username', 'service_user', 'Default service account username for MikroTik devices'),
            ('mikrotik_service_password', 'service_password123', 'Default service account password for MikroTik devices'),
            ('default_temp_user_prefix', 'temp_', 'Prefix for temporary usernames'),
            ('max_concurrent_sessions', '10', 'Maximum concurrent sessions per user'),
            ('session_cleanup_interval', '300', 'Session cleanup interval in seconds'),
            ('log_retention_days', '90', 'Number of days to retain activity logs'),
            ('enable_email_notifications', 'false', 'Enable email notifications for credential requests'),
            ('system_timezone', 'UTC', 'System timezone'),
        ]
        
        for key, value, description in default_settings:
            cursor.execute("""
                INSERT IGNORE INTO system_settings (setting_key, setting_value, description)
                VALUES (%s, %s, %s)
            """, (key, value, description))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("✓ Default system settings inserted")
        
    except Error as e:
        print(f"✗ Error inserting default settings: {e}")
        return False
    
    return True

def test_connection():
    """Test database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        connection.close()
        print("✓ Database connection test successful")
        return True
    except Error as e:
        print(f"✗ Database connection test failed: {e}")
        return False

def main():
    """Main initialization function"""
    print("🚀 Initializing MikroTik Credential Manager Database...")
    print("=" * 60)
    
    # Step 1: Create database
    if not create_database():
        print("❌ Database initialization failed!")
        return False
    
    # Step 2: Test connection
    if not test_connection():
        print("❌ Database connection failed!")
        return False
    
    # Step 3: Create tables
    if not create_tables():
        print("❌ Table creation failed!")
        return False
    
    # Step 4: Create admin user
    if not create_admin_user():
        print("❌ Admin user creation failed!")
        return False
    
    # Step 5: Insert default settings
    if not insert_default_settings():
        print("❌ Default settings insertion failed!")
        return False
    
    print("=" * 60)
    print("✅ Database initialization completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Update the .env file with your database credentials")
    print("2. Update MikroTik service account credentials in system settings")
    print("3. Run the application: python main.py")
    print("4. Login with admin credentials and change the password")
    
    return True

if __name__ == "__main__":
    main()