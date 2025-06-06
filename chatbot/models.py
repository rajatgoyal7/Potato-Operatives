from datetime import datetime
from config.database import db
from sqlalchemy.dialects.postgresql import JSON
import json

class Booking(db.Model):
    """Model for storing booking information"""
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(100), unique=True, nullable=False)
    guest_name = db.Column(db.String(200), nullable=False)
    guest_email = db.Column(db.String(200), nullable=False)
    guest_phone = db.Column(db.String(20))
    hotel_name = db.Column(db.String(200), nullable=False)
    hotel_location = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    check_in_date = db.Column(db.Date)
    check_out_date = db.Column(db.Date)
    guest_language = db.Column(db.String(10), default='en')

    # Additional fields for external booking events
    reference_number = db.Column(db.String(100))  # External reference number
    hotel_id = db.Column(db.String(50))  # External hotel ID
    booking_status = db.Column(db.String(50), default='reserved')  # Booking status
    booking_source = db.Column(JSON)  # Source information (channel, application, etc.)
    raw_event_data = db.Column(JSON)  # Store raw event data for debugging

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    chat_sessions = db.relationship('ChatSession', backref='booking', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'guest_name': self.guest_name,
            'guest_email': self.guest_email,
            'guest_phone': self.guest_phone,
            'hotel_name': self.hotel_name,
            'hotel_location': self.hotel_location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'guest_language': self.guest_language,
            'reference_number': self.reference_number,
            'hotel_id': self.hotel_id,
            'booking_status': self.booking_status,
            'booking_source': self.booking_source
        }

class ChatSession(db.Model):
    """Model for storing chat sessions"""
    __tablename__ = 'chat_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    guest_language = db.Column(db.String(10), default='en')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = db.relationship('ChatMessage', backref='session', lazy=True)

class ChatMessage(db.Model):
    """Model for storing chat messages"""
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # 'user', 'bot', 'system'
    content = db.Column(db.Text, nullable=False)
    message_metadata = db.Column(JSON)  # Store additional data like recommendations
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'message_type': self.message_type,
            'content': self.content,
            'metadata': self.message_metadata,
            'timestamp': self.timestamp.isoformat()
        }

class Recommendation(db.Model):
    """Model for caching recommendations"""
    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)
    location_key = db.Column(db.String(200), nullable=False)  # lat_lng_category
    category = db.Column(db.String(50), nullable=False)  # restaurant, sightseeing, events
    data = db.Column(JSON, nullable=False)
    language = db.Column(db.String(10), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class UserPreference(db.Model):
    """Model for storing user preferences"""
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    guest_email = db.Column(db.String(200), nullable=False)
    preferences = db.Column(JSON)  # Store user preferences as JSON
    language = db.Column(db.String(10), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
