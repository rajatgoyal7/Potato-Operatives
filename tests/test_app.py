import pytest
import json
from app import create_app
from config.database import db
from chatbot.models import Booking, ChatSession

@pytest.fixture
def app():
    """Create test application"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def sample_booking_event():
    """Sample booking event data"""
    return {
        "event_type": "booking.created",
        "booking": {
            "booking_id": "TEST123",
            "guest_name": "Test User",
            "guest_email": "test@example.com",
            "guest_phone": "+91-9876543210",
            "hotel_name": "Test Hotel",
            "hotel_location": "Test Location, Test City",
            "check_in_date": "2024-01-15",
            "check_out_date": "2024-01-17",
            "guest_language": "en"
        }
    }

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data

def test_booking_webhook(client, sample_booking_event):
    """Test booking webhook endpoint"""
    response = client.post(
        '/webhook/booking',
        data=json.dumps(sample_booking_event),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['booking_id'] == 'TEST123'

def test_create_chat_session(client, sample_booking_event):
    """Test chat session creation"""
    # First create a booking
    client.post(
        '/webhook/booking',
        data=json.dumps(sample_booking_event),
        content_type='application/json'
    )
    
    # Then create chat session
    response = client.post(
        '/chat/session',
        data=json.dumps({
            'booking_id': 'TEST123',
            'language': 'en'
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'session_id' in data
    assert data['booking']['booking_id'] == 'TEST123'

def test_send_message(client, sample_booking_event):
    """Test sending message to chatbot"""
    # Create booking and session
    client.post(
        '/webhook/booking',
        data=json.dumps(sample_booking_event),
        content_type='application/json'
    )
    
    session_response = client.post(
        '/chat/session',
        data=json.dumps({
            'booking_id': 'TEST123',
            'language': 'en'
        }),
        content_type='application/json'
    )
    
    session_data = json.loads(session_response.data)
    session_id = session_data['session_id']
    
    # Send message
    response = client.post(
        '/chat/message',
        data=json.dumps({
            'session_id': session_id,
            'message': 'I want restaurant recommendations'
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'response' in data
    assert 'messages' in data

def test_get_booking(client, sample_booking_event):
    """Test get booking endpoint"""
    # Create booking
    client.post(
        '/webhook/booking',
        data=json.dumps(sample_booking_event),
        content_type='application/json'
    )
    
    # Get booking
    response = client.get('/booking/TEST123')
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['booking_id'] == 'TEST123'
    assert data['guest_name'] == 'Test User'

def test_get_stats(client):
    """Test admin stats endpoint"""
    response = client.get('/admin/stats')
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'total_bookings' in data
    assert 'total_sessions' in data
    assert 'active_sessions' in data

def test_invalid_booking_webhook(client):
    """Test webhook with invalid data"""
    response = client.post(
        '/webhook/booking',
        data=json.dumps({'invalid': 'data'}),
        content_type='application/json'
    )
    
    assert response.status_code == 400

def test_nonexistent_booking(client):
    """Test accessing nonexistent booking"""
    response = client.get('/booking/NONEXISTENT')
    
    assert response.status_code == 404
