#!/usr/bin/env python3
"""
Fix admin password to use bcrypt hashing
"""

import mysql.connector
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

def fix_admin_password():
    try:
        # Initialize password context (same as in auth.py)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Connect to database
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'mikrotik_cred_manager')
        )
        cursor = conn.cursor()
        
        # Generate proper bcrypt hash for admin123
        password = "admin123"
        bcrypt_hash = pwd_context.hash(password)
        
        print(f"🔧 Updating admin password with bcrypt hash...")
        print(f"   Password: {password}")
        print(f"   New hash: {bcrypt_hash[:30]}...")
        
        # Update admin user password
        cursor.execute("UPDATE users SET password_hash = %s WHERE username = 'admin'", (bcrypt_hash,))
        conn.commit()
        
        # Verify the update
        cursor.execute("SELECT username, password_hash FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        
        if result:
            username, stored_hash = result
            # Test verification
            is_valid = pwd_context.verify(password, stored_hash)
            print(f"✅ Password updated successfully!")
            print(f"   Verification test: {'✅ PASS' if is_valid else '❌ FAIL'}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🔑 Updated Login Credentials:")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   URL: http://localhost:8000")
        print(f"\n✅ You can now login to the application!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_admin_password()