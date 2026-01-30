#!/usr/bin/env python3
"""
Migration Script: Convert existing portfolio.db to encrypted portfolio_encrypted.db

This script will:
1. Prompt for a new password
2. Create an encrypted database
3. Migrate all existing data
4. Set up password authentication

IMPORTANT: Store your password securely. It cannot be recovered!
"""

import os
import getpass
from database_encryption import DatabaseEncryptionManager

def main():
    print("=" * 60)
    print("Portfolio Tracker - Database Encryption Migration")
    print("=" * 60)
    
    # Check if existing database exists
    old_db_path = 'portfolio.db'
    if not os.path.exists(old_db_path):
        print(f"❌ Existing database '{old_db_path}' not found.")
        print("This migration script is for converting existing unencrypted databases.")
        print("\nIf you want to create a new encrypted database, just run the app normally.")
        return
    
    print(f"📁 Found existing database: {old_db_path}")
    
    # Get password from user
    while True:
        print("\n" + "-" * 40)
        print("🔐 Create a strong password for your encrypted database")
        print("Requirements:")
        print("  • At least 8 characters")
        print("  • Mix of uppercase and lowercase")
        print("  • Include numbers")
        print("  • Special characters recommended")
        print("  ⚠️  Store this password securely - it cannot be recovered!")
        print("-" * 40)
        
        password = getpass.getpass("Enter new password: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("❌ Passwords do not match. Please try again.")
            continue
        
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long.")
            continue
        
        # Check password strength
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            print("⚠️  Password should contain uppercase, lowercase, and numbers for better security.")
            proceed = input("Continue with this password anyway? (y/N): ").lower()
            if proceed != 'y':
                continue
        
        break
    
    # Perform migration
    print(f"\n🔄 Starting migration...")
    
    try:
        # Initialize database encryption manager
        db_encryption = DatabaseEncryptionManager('portfolio_encrypted.db')
        
        # Initialize new database with schema
        print("📋 Creating database schema...")
        if not db_encryption.init_database(password):
            print("❌ Failed to initialize database schema.")
            return
        
        # Migrate existing data
        print("📦 Migrating existing data...")
        if not db_encryption.migrate_existing_database(old_db_path, password):
            print("❌ Failed to migrate existing data.")
            return
        
        print("✅ Migration completed successfully!")
        print(f"\n📁 New encrypted database: portfolio_encrypted.db")
        print(f"📁 Original database: {old_db_path} (unchanged)")
        
        print("\n🎉 Setup complete! You can now:")
        print("1. Run the portfolio tracker app: python app.py")
        print("2. Visit http://127.0.0.1:5000")
        print("3. Enter your password to unlock the database")
        
        print(f"\n⚠️  IMPORTANT: Keep your password secure!")
        print("   Without it, your data will be permanently lost.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("Please check the error above and try again.")

if __name__ == '__main__':
    main()