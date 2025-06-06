# Database Migrations

This folder contains database migration scripts for the Treebo Chatbot system.

## Current Migration

### `init_database.py` - Complete Database Setup

This is the **single comprehensive migration** that creates the entire database schema from scratch.

**Database Location:** `instance/treebo_chatbot.db` (Flask instance folder)

**What it creates:**

1. **`users`** - User authentication and session management
2. **`bookings`** - Booking information from external API and webhooks
3. **`chat_sessions`** - Chat sessions linked to bookings
4. **`chat_messages`** - Individual chat messages
5. **`recommendations`** - Cached recommendations for performance

**Features:**
- ✅ Creates all tables with proper relationships
- ✅ Adds performance indexes
- ✅ Handles existing databases gracefully
- ✅ Uses Flask instance folder (correct location)
- ✅ Creates instance directory if missing
- ✅ Provides detailed verification output
- ✅ Optional cleanup of old tables
- ✅ Works standalone (no Flask dependencies required)

## Usage

### Initialize Database
```bash
python3 migrations/init_database.py
```

### What the script does:
1. Creates instance directory if missing
2. Checks current database state in instance folder
3. Creates missing tables using raw SQL
4. Adds performance indexes
5. Verifies the final structure
6. Shows table row counts
7. Optionally cleans up old tables

### Safe to run multiple times
The script uses `CREATE TABLE IF NOT EXISTS` so it's safe to run multiple times without data loss.

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200),
    email VARCHAR(200),
    session_token VARCHAR(100) UNIQUE,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bookings table  
CREATE TABLE bookings (
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
);

-- Chat sessions table
CREATE TABLE chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    booking_id INTEGER NOT NULL,
    guest_language VARCHAR(10) DEFAULT 'en',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings (id)
);

-- Chat messages table
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    message_metadata TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
);

-- Recommendations table
CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_key VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    data TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL
);
```

## Performance Indexes

The migration automatically creates these indexes for optimal performance:

- `idx_users_phone` - Fast user lookup by phone number
- `idx_users_session_token` - Fast session validation
- `idx_bookings_booking_id` - Fast booking lookup
- `idx_chat_sessions_session_id` - Fast chat session lookup
- `idx_chat_sessions_booking_id` - Fast booking-to-sessions lookup
- `idx_chat_messages_session_id` - Fast message retrieval
- `idx_recommendations_location_key` - Fast recommendation lookup
- `idx_recommendations_expires_at` - Fast cache expiration cleanup

## Migration History

This replaces the previous multiple migration files:
- ❌ `add_user_table.py` (removed)
- ❌ `add_booking_fields.py` (removed) 
- ❌ `remove_user_preferences.py` (removed)

All functionality has been consolidated into the single `init_database.py` script.
