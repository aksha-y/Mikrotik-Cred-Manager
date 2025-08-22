#!/usr/bin/env python3
"""
Simple database setup script for XAMPP MySQL
"""

import mysql.connector
from mysql.connector import Error
import hashlib
import secrets
from datetime import datetime
import os

# XAMPP MySQL default configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',  # XAMPP default has no password
}

DB_NAME = 'mikrotik_cred_manager'

def create_database():
    """Create the database if it doesn't exist"""
    try:
        print("🔌 Connecting to MySQL...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"✅ Database '{DB_NAME}' created successfully")
        
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_tables():
    """Create all required tables"""
    try:
        # Connect to the specific database
        config = DB_CONFIG.copy()
        config['database'] = DB_NAME
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        print("📋 Creating tables...")
        
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
        print("  ✅ Users table created")
        
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
                expires_at DATETIME NOT NULL,
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
        print("  ✅ Credential requests table created")
        
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
        print("  ✅ Activity logs table created")
        
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
        print("  ✅ System settings table created")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return True
        
    except Error as e:
        print(f"❌ Error creating tables: {e}")
        return False

def create_admin_user():
    """Create default admin user"""
    try:
        config = DB_CONFIG.copy()
        config['database'] = DB_NAME
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Check if admin user already exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if cursor.fetchone():
            print("ℹ️  Admin user already exists")
            cursor.close()
            connection.close()
            return True
        
        # Generate admin password
        admin_password = "admin123"  # Simple password for initial setup
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
        
        print("✅ Admin user created successfully")
        print("📋 Admin Credentials:")
        print(f"   Username: admin")
        print(f"   Password: {admin_password}")
        print("   ⚠️  Please change this password after first login!")
        
        return True
        
    except Error as e:
        print(f"❌ Error creating admin user: {e}")
        return False

def insert_sample_data():
    """Insert some sample data for testing"""
    try:
        config = DB_CONFIG.copy()
        config['database'] = DB_NAME
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Insert sample users
        sample_users = [
            ('john_doe', 'john@company.com', 'John Doe', 'full_access'),
            ('jane_smith', 'jane@company.com', 'Jane Smith', 'write_access'),
            ('bob_wilson', 'bob@company.com', 'Bob Wilson', 'read_only')
        ]
        
        for username, email, full_name, role in sample_users:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if not cursor.fetchone():
                password_hash = hashlib.sha256("password123".encode()).hexdigest()
                cursor.execute("""
                    INSERT INTO users (username, email, full_name, password_hash, role, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (username, email, full_name, password_hash, role, True))
        
        # Insert system settings
        default_settings = [
            ('mikrotik_service_username', 'service_user', 'Default service account username for MikroTik devices'),
            ('mikrotik_service_password', 'service_password123', 'Default service account password for MikroTik devices'),
            ('default_temp_user_prefix', 'temp_', 'Prefix for temporary usernames'),
            ('max_concurrent_sessions', '10', 'Maximum concurrent sessions per user'),
            ('session_cleanup_interval', '300', 'Session cleanup interval in seconds'),
            ('log_retention_days', '90', 'Number of days to retain activity logs'),
        ]
        
        for key, value, description in default_settings:
            cursor.execute("""
                INSERT IGNORE INTO system_settings (setting_key, setting_value, description)
                VALUES (%s, %s, %s)
            """, (key, value, description))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("✅ Sample data inserted successfully")
        print("📋 Sample User Credentials (password: password123):")
        for username, email, full_name, role in sample_users:
            print(f"   {username} ({role})")
        
        return True
        
    except Error as e:
        print(f"❌ Error inserting sample data: {e}")
        return False

def test_connection():
    """Test database connection"""
    try:
        print("🧪 Testing database connection...")
        config = DB_CONFIG.copy()
        config['database'] = DB_NAME
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.close()
        connection.close()
        
        print(f"✅ Database connection successful! Found {user_count} users.")
        return True
        
    except Error as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up MikroTik Credential Manager Database (XAMPP)")
    print("=" * 60)
    
    # Check if MySQL is running
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        connection.close()
        print("✅ MySQL connection successful")
    except Error as e:
        print(f"❌ Cannot connect to MySQL. Is XAMPP running?")
        print(f"   Error: {e}")
        return False
    
    # Step 1: Create database
    if not create_database():
        return False
    
    # Step 2: Create tables
    if not create_tables():
        return False
    
    # Step 3: Create admin user
    if not create_admin_user():
        return False
    
    # Step 4: Insert sample data
    if not insert_sample_data():
        return False
    
    # Step 5: Test connection
    if not test_connection():
        return False
    
    print("=" * 60)
    print("🎉 Database setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Start the application: python run.py")
    print("2. Open browser: http://localhost:8000")
    print("3. Login with admin credentials shown above")
    print("4. Change the admin password immediately")
    
    return True

if __name__ == "__main__":
    main()