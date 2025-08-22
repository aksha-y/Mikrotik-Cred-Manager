#!/usr/bin/env python3
"""
Fix all user passwords to use bcrypt hashing
"""

import mysql.connector
from passlib.context import CryptContext

def fix_all_passwords():
    try:
        # Initialize password context (same as in auth.py)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Connect to database
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='mikrotik_cred_manager'
        )
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute("SELECT username FROM users")
        users = cursor.fetchall()
        
        print(f"🔧 Updating passwords for {len(users)} users...")
        
        # Update each user with proper bcrypt hash
        for (username,) in users:
            if username == 'admin':
                password = "admin123"
            else:
                password = "password123"  # Default password for sample users
            
            bcrypt_hash = pwd_context.hash(password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s", (bcrypt_hash, username))
            print(f"   ✅ Updated {username} (password: {password})")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n🎉 All passwords updated successfully!")
        print(f"\n🔑 Login Credentials:")
        print(f"   Admin: admin / admin123")
        print(f"   Sample users: john_doe, jane_smith, bob_wilson / password123")
        print(f"   URL: http://localhost:8000")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_all_passwords()