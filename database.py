import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'mikrotik_cred_manager'),
    'user': os.getenv('DB_USER', 'your_db_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'autocommit': True
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection; create DB if missing in local dev"""
        try:
            # First try with provided DB
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            logging.info("Database connection established successfully")
            return True
        except Error as e:
            msg = str(e)
            logging.warning(f"Initial DB connect failed: {msg}")
            # Try to create database if missing (only when using root or privileged user)
            try:
                cfg = DB_CONFIG.copy()
                db_name = cfg.pop('database', None)
                tmp_conn = mysql.connector.connect(**cfg)
                tmp_cursor = tmp_conn.cursor()
                if db_name:
                    tmp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
                    logging.info(f"Database `{db_name}` ensured (created if missing)")
                tmp_cursor.close()
                tmp_conn.close()
                # Retry connection
                self.connection = mysql.connector.connect(**DB_CONFIG)
                self.cursor = self.connection.cursor(dictionary=True)
                logging.info("Database connection established successfully after creating DB")
                return True
            except Error as e2:
                logging.error(f"Error connecting to database after create attempt: {e2}")
                return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logging.info("Database connection closed")
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            self.cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                return self.cursor.fetchall()
            else:
                self.connection.commit()
                return self.cursor.rowcount
        except Error as e:
            logging.error(f"Database query error: {e}")
            if self.connection:
                self.connection.rollback()
            raise e
    
    def create_tables(self):
        """Create all necessary tables"""
        tables = {
            'users': """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    role ENUM('admin', 'full_access', 'read_only', 'write_access') DEFAULT 'read_only',
                    allowed_duration_minutes INT DEFAULT 30,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """,
            'mikrotik_devices': """
                CREATE TABLE IF NOT EXISTS mikrotik_devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    wan_ip VARCHAR(45) UNIQUE NOT NULL,
                    device_name VARCHAR(100),
                    location VARCHAR(200),
                    notes TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """,
            'credential_requests': """
                CREATE TABLE IF NOT EXISTS credential_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    wan_ip VARCHAR(45) NOT NULL,
                    purpose TEXT NOT NULL,
                    duration_minutes INT NOT NULL,
                    temp_username VARCHAR(100) NOT NULL,
                    temp_password VARCHAR(100) NOT NULL,
                    status ENUM('active', 'expired', 'revoked') DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    revoked_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """,
            'activity_logs': """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    action VARCHAR(100) NOT NULL,
                    target_ip VARCHAR(45),
                    details TEXT,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    status ENUM('success', 'failed', 'error') DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """,
            'sessions': """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    session_token VARCHAR(255) UNIQUE NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
        }
        
        try:
            for table_name, query in tables.items():
                self.execute_query(query)
                logging.info(f"Table '{table_name}' created/verified successfully")

            # Schema upgrades / safe alters
            try:
                self.execute_query("ALTER TABLE credential_requests ADD COLUMN device_identity VARCHAR(200) NULL AFTER wan_ip")
                logging.info("Column 'device_identity' added to 'credential_requests'")
            except Error as e:
                # MySQL error 1060 = Duplicate column name
                logging.info(f"Schema check: device_identity column present or alter skipped: {e}")
            try:
                self.execute_query("ALTER TABLE activity_logs ADD COLUMN target_identity VARCHAR(200) NULL AFTER target_ip")
                logging.info("Column 'target_identity' added to 'activity_logs'")
            except Error as e:
                logging.info(f"Schema check: target_identity column present or alter skipped: {e}")
            # Add allowed_duration_minutes to users if missing
            try:
                self.execute_query("ALTER TABLE users ADD COLUMN allowed_duration_minutes INT DEFAULT 30 AFTER role")
                logging.info("Column 'allowed_duration_minutes' added to 'users'")
            except Error as e:
                logging.info(f"Schema check: allowed_duration_minutes present or alter skipped: {e}")
            
            # Create default admin user if not exists
            self.create_default_admin()
            
        except Error as e:
            logging.error(f"Error creating tables: {e}")
            raise e
    
    def create_default_admin(self):
        """Create default admin user with a random password printed to logs once."""
        from auth import hash_password
        import secrets
        
        check_admin = "SELECT id FROM users WHERE username = 'admin'"
        result = self.execute_query(check_admin)
        
        if not result:
            # Use fixed password from env for local setups if provided; otherwise generate random
            local_pw = os.getenv("ADMIN_DEFAULT_PASSWORD")
            raw_password = local_pw if local_pw else secrets.token_urlsafe(12)
            password_hash = hash_password(raw_password)
            insert_admin = """
                INSERT INTO users (username, email, password_hash, full_name, role, allowed_duration_minutes, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.execute_query(insert_admin, (
                'admin', 
                'admin@example.com', 
                password_hash, 
                'System Administrator', 
                'admin', 
                180,
                True
            ))
            logging.warning("Default admin user created.")
            logging.warning("Admin username: admin")
            logging.warning(f"Admin password: {raw_password}")

# Global database instance
db = DatabaseManager()

def init_database():
    """Initialize database connection and create tables"""
    if db.connect():
        db.create_tables()
        return True
    return False