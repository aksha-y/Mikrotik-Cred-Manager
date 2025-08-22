#!/usr/bin/env python3
"""
Check admin user credentials in database
"""

import mysql.connector
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

def check_admin_user():
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'mikrotik_cred_manager')
        )
        cursor = conn.cursor()
        
        # Check admin user
        cursor.execute("SELECT username, password_hash, role FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        
        if result:
            username, stored_hash, role = result
            print(f"✅ Admin user found:")
            print(f"   Username: {username}")
            print(f"   Role: {role}")
            print(f"   Password Hash: {stored_hash[:20]}...")
            
            # Test password hashing
            test_password = "admin123"
            test_hash = hashlib.sha256(test_password.encode()).hexdigest()
            
            print(f"\n🔍 Password verification:")
            print(f"   Test password: {test_password}")
            print(f"   Test hash: {test_hash[:20]}...")
            print(f"   Hashes match: {'✅ YES' if test_hash == stored_hash else '❌ NO'}")
            
            if test_hash != stored_hash:
                print(f"\n🔧 Updating admin password...")
                cursor.execute("UPDATE users SET password_hash = %s WHERE username = 'admin'", (test_hash,))
                conn.commit()
                print("✅ Admin password updated successfully!")
        else:
            print("❌ Admin user not found!")
            
            # Create admin user
            print("🔧 Creating admin user...")
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (username, email, full_name, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ('admin', 'admin@company.com', 'System Administrator', password_hash, 'admin', True))
            conn.commit()
            print("✅ Admin user created successfully!")
        
        cursor.close()
        conn.close()
        
        print(f"\n🔑 Login Credentials:")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   URL: http://localhost:8000")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_admin_user()