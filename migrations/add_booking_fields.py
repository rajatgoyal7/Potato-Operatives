#!/usr/bin/env python3
"""
Database migration to add new fields to the Booking model for external booking events.

This migration adds the following fields:
- reference_number: External reference number from booking service
- hotel_id: External hotel ID
- booking_status: Status of the booking (reserved, confirmed, cancelled, etc.)
- booking_source: JSON field to store source information (channel, application, etc.)
- raw_event_data: JSON field to store raw event data for debugging

Run this script to update your database schema.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import db
from app import create_app
from sqlalchemy import text

def run_migration():
    """Run the database migration"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting database migration...")
            
            # Check if columns already exist
            result = db.engine.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'bookings' 
                AND column_name IN ('reference_number', 'hotel_id', 'booking_status', 'booking_source', 'raw_event_data')
            """))
            
            existing_columns = [row[0] for row in result]
            
            # Add new columns if they don't exist
            if 'reference_number' not in existing_columns:
                db.engine.execute(text("ALTER TABLE bookings ADD COLUMN reference_number VARCHAR(100)"))
                print("✓ Added reference_number column")
            
            if 'hotel_id' not in existing_columns:
                db.engine.execute(text("ALTER TABLE bookings ADD COLUMN hotel_id VARCHAR(50)"))
                print("✓ Added hotel_id column")
            
            if 'booking_status' not in existing_columns:
                db.engine.execute(text("ALTER TABLE bookings ADD COLUMN booking_status VARCHAR(50) DEFAULT 'reserved'"))
                print("✓ Added booking_status column")
            
            if 'booking_source' not in existing_columns:
                db.engine.execute(text("ALTER TABLE bookings ADD COLUMN booking_source JSON"))
                print("✓ Added booking_source column")
            
            if 'raw_event_data' not in existing_columns:
                db.engine.execute(text("ALTER TABLE bookings ADD COLUMN raw_event_data JSON"))
                print("✓ Added raw_event_data column")
            
            # Make check_in_date and check_out_date nullable since external events might not always have them
            db.engine.execute(text("ALTER TABLE bookings ALTER COLUMN check_in_date DROP NOT NULL"))
            db.engine.execute(text("ALTER TABLE bookings ALTER COLUMN check_out_date DROP NOT NULL"))
            print("✓ Made date columns nullable")
            
            # Commit the changes
            db.session.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    run_migration()
