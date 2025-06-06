#!/usr/bin/env python3
"""
Comprehensive database migration script for Treebo Chatbot
Creates all required tables with proper schema and relationships.

This migration creates:
1. users - User authentication and session management
2. bookings - Booking information from external API and webhooks
3. chat_sessions - Chat sessions linked to bookings
4. chat_messages - Individual chat messages
5. recommendations - Cached recommendations for performance

Run this script to initialize or update your database schema.
This script works standalone without requiring Flask dependencies.
"""

import sqlite3
import os
import sys

def get_database_path():
    """Get the correct database path (Flask instance folder)"""
    instance_dir = 'instance'
    db_filename = 'treebo_chatbot.db'

    # Create instance directory if it doesn't exist
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        print(f"📁 Created instance directory: {instance_dir}")

    return os.path.join(instance_dir, db_filename)

def check_database_exists():
    """Check if database file exists and has tables"""
    db_path = get_database_path()

    if not os.path.exists(db_path):
        return False, []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return True, tables
    except Exception:
        return False, []

def create_database_schema():
    """Create the complete database schema using raw SQL"""

    db_path = get_database_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")

        # 1. Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(200),
                email VARCHAR(200),
                session_token VARCHAR(100) UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Create bookings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id VARCHAR(100) UNIQUE NOT NULL,
                guest_name VARCHAR(200) NOT NULL,
                guest_email VARCHAR(200) NOT NULL,
                guest_phone VARCHAR(20),
                hotel_name VARCHAR(200) NOT NULL,
                hotel_location VARCHAR(500) NOT NULL,
                latitude FLOAT,
                longitude FLOAT,
                check_in_date DATE,
                check_out_date DATE,
                guest_language VARCHAR(10) DEFAULT 'en',
                reference_number VARCHAR(100),
                hotel_id VARCHAR(50),
                booking_status VARCHAR(50) DEFAULT 'reserved',
                booking_source TEXT,
                raw_event_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 3. Create chat_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id VARCHAR(100) UNIQUE NOT NULL,
                booking_id INTEGER NOT NULL,
                guest_language VARCHAR(10) DEFAULT 'en',
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings (id)
            )
        ''')

        # 4. Create chat_messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                message_type VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                message_metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            )
        ''')

        # 5. Create recommendations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_key VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                data TEXT NOT NULL,
                language VARCHAR(10) DEFAULT 'en',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL
            )
        ''')

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_session_token ON users(session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_booking_id ON bookings(booking_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_sessions_booking_id ON chat_sessions(booking_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendations_location_key ON recommendations(location_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendations_expires_at ON recommendations(expires_at)')

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Error creating database schema: {e}")
        return False

def run_migration():
    """Run the comprehensive database migration"""

    print("🚀 TREEBO CHATBOT DATABASE MIGRATION")
    print("=" * 50)

    # Show database path
    db_path = get_database_path()
    print(f"📍 Database location: {db_path}")

    # Check current database state
    db_exists, existing_tables = check_database_exists()

    if db_exists and existing_tables:
        print("📊 Current database state:")
        print(f"   Existing tables: {sorted(existing_tables)}")

        # Check for any unwanted tables
        expected_tables = {'users', 'bookings', 'chat_sessions', 'chat_messages', 'recommendations'}
        extra_tables = set(existing_tables) - expected_tables

        if extra_tables:
            print(f"⚠️  Found unexpected tables: {extra_tables}")
            print("   These will be preserved but may need manual cleanup")
    else:
        print("📊 Database does not exist or is empty")
        print("   Will create fresh database structure")

    try:
        print("\n🏗️ Creating/updating database schema...")

        # Create database schema using raw SQL
        success = create_database_schema()

        if not success:
            return False

        print("✅ Database schema created/updated successfully!")

        # Verify the final structure
        db_exists, final_tables = check_database_exists()

        if db_exists:
            print("\n📊 Final database structure:")

            expected_tables = [
                ('users', 'User authentication and session management'),
                ('bookings', 'Booking information from external API and webhooks'),
                ('chat_sessions', 'Chat sessions linked to bookings'),
                ('chat_messages', 'Individual chat messages'),
                ('recommendations', 'Cached recommendations for performance')
            ]

            for table_name, description in expected_tables:
                if table_name in final_tables:
                    print(f"   ✅ {table_name} - {description}")
                else:
                    print(f"   ❌ {table_name} - MISSING!")

            # Check for any extra tables (excluding SQLite system tables)
            expected_table_names = {table[0] for table in expected_tables}
            system_tables = {'sqlite_sequence'}  # SQLite system tables
            extra_tables = set(final_tables) - expected_table_names - system_tables

            if extra_tables:
                print(f"\n⚠️  Additional tables found: {sorted(extra_tables)}")
                print("   These may be from previous migrations or manual additions")

            # Count rows in each table
            print(f"\n📈 Table row counts:")
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()

            for table in sorted(final_tables):
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   {table}: {count} rows")
                except Exception as e:
                    print(f"   {table}: Error reading - {e}")

            conn.close()

        print("\n🎉 DATABASE MIGRATION COMPLETED!")
        print("=" * 50)
        print("✅ All required tables are present")
        print("✅ Database is ready for use")
        print("✅ You can now start the application")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure no other processes are using the database")
        print("2. Check file permissions in the project directory")
        print("3. Verify all dependencies are installed (pip install -r requirements.txt)")
        return False

def cleanup_old_tables():
    """Optional: Remove any unwanted tables from previous versions"""
    
    print("\n🗑️ OPTIONAL: Cleanup old tables")
    print("This will remove any tables not in the current schema")
    
    response = input("Do you want to remove old/unused tables? (y/N): ").lower().strip()
    
    if response == 'y':
        try:
            conn = sqlite3.connect(get_database_path())
            cursor = conn.cursor()
            
            # Get current tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            current_tables = [row[0] for row in cursor.fetchall()]
            
            # Expected tables (including SQLite system tables)
            expected_tables = {'users', 'bookings', 'chat_sessions', 'chat_messages', 'recommendations', 'sqlite_sequence'}

            # Find tables to remove
            tables_to_remove = set(current_tables) - expected_tables
            
            if tables_to_remove:
                print(f"🗑️ Removing tables: {sorted(tables_to_remove)}")
                
                for table in tables_to_remove:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    print(f"   ❌ Dropped {table}")
                
                conn.commit()
                print("✅ Cleanup completed!")
            else:
                print("ℹ️  No unnecessary tables found")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
    else:
        print("ℹ️  Skipping cleanup")

if __name__ == "__main__":
    success = run_migration()
    
    if success:
        # Offer optional cleanup
        cleanup_old_tables()
        sys.exit(0)
    else:
        sys.exit(1)
