#!/usr/bin/env python3
"""
Example usage script for Treebo Chatbot API
This script demonstrates how to interact with the chatbot system
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000"
HEADERS = {"Content-Type": "application/json"}

def create_sample_booking():
    """Create a sample booking event"""
    booking_event = {
        "event_type": "booking.created",
        "booking": {
            "booking_id": "TRB123456",
            "guest_name": "John Doe",
            "guest_email": "john.doe@example.com",
            "guest_phone": "+91-9876543210",
            "hotel_name": "Treebo Trend Hotel",
            "hotel_location": "Connaught Place, New Delhi, India",
            "check_in_date": "2024-01-15",
            "check_out_date": "2024-01-17",
            "guest_language": "en"
        }
    }
    
    print("🏨 Creating sample booking...")
    response = requests.post(
        f"{BASE_URL}/webhook/booking",
        headers=HEADERS,
        data=json.dumps(booking_event)
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Booking created successfully!")
        print(f"   Booking ID: {result['booking_id']}")
        print(f"   Session ID: {result['session_id']}")
        return result['session_id']
    else:
        print(f"❌ Failed to create booking: {response.text}")
        return None

def create_chat_session(booking_id, language="en"):
    """Create a chat session for a booking"""
    session_data = {
        "booking_id": booking_id,
        "language": language
    }
    
    print(f"💬 Creating chat session for booking {booking_id}...")
    response = requests.post(
        f"{BASE_URL}/chat/session",
        headers=HEADERS,
        data=json.dumps(session_data)
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Chat session created!")
        print(f"   Session ID: {result['session_id']}")
        return result['session_id']
    else:
        print(f"❌ Failed to create chat session: {response.text}")
        return None

def send_message(session_id, message):
    """Send a message to the chatbot"""
    message_data = {
        "session_id": session_id,
        "message": message
    }
    
    print(f"👤 User: {message}")
    response = requests.post(
        f"{BASE_URL}/chat/message",
        headers=HEADERS,
        data=json.dumps(message_data)
    )
    
    if response.status_code == 200:
        result = response.json()
        bot_response = result['response']['message']
        print(f"🤖 Bot: {bot_response}")
        return result
    else:
        print(f"❌ Failed to send message: {response.text}")
        return None

def get_recommendations(session_id, category):
    """Get recommendations for a specific category"""
    print(f"🔍 Getting {category} recommendations...")
    response = requests.get(f"{BASE_URL}/chat/recommendations/{session_id}/{category}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Found {len(result['recommendations'])} {category} recommendations!")
        
        for i, rec in enumerate(result['recommendations'][:3], 1):
            print(f"   {i}. {rec.get('name', 'Unknown')}")
            if rec.get('rating'):
                print(f"      ⭐ Rating: {rec['rating']}/5")
            if rec.get('distance'):
                print(f"      📍 Distance: {rec['distance']} km")
        
        return result
    else:
        print(f"❌ Failed to get recommendations: {response.text}")
        return None

def get_chat_history(session_id):
    """Get chat history for a session"""
    print(f"📜 Getting chat history...")
    response = requests.get(f"{BASE_URL}/chat/history/{session_id}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Chat history retrieved!")
        print(f"   Total messages: {len(result['messages'])}")
        return result
    else:
        print(f"❌ Failed to get chat history: {response.text}")
        return None

def demo_multilingual():
    """Demonstrate multi-language support"""
    print("\n🌍 Multi-language Demo")
    print("=" * 50)
    
    # Create booking with Hindi language
    booking_event = {
        "event_type": "booking.created",
        "booking": {
            "booking_id": "TRB789012",
            "guest_name": "राज शर्मा",
            "guest_email": "raj.sharma@example.com",
            "hotel_name": "Treebo Trend Hotel",
            "hotel_location": "Connaught Place, New Delhi, India",
            "check_in_date": "2024-01-15",
            "check_out_date": "2024-01-17",
            "guest_language": "hi"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/webhook/booking",
        headers=HEADERS,
        data=json.dumps(booking_event)
    )
    
    if response.status_code == 200:
        result = response.json()
        session_id = result['session_id']
        
        # Send message in Hindi
        send_message(session_id, "मुझे रेस्तरां की सिफारिशें चाहिए")
        
        # Get recommendations
        get_recommendations(session_id, "restaurants")

def main():
    """Main demonstration function"""
    print("🚀 Treebo Chatbot Demo")
    print("=" * 50)
    
    # Check if service is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Chatbot service is not running!")
            print("   Please start the service with: docker-compose up -d")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to chatbot service!")
        print("   Please start the service with: docker-compose up -d")
        return
    
    print("✅ Chatbot service is running!")
    print()
    
    # Create booking and get session ID
    session_id = create_sample_booking()
    if not session_id:
        return
    
    print()
    
    # Simulate conversation
    conversation = [
        "Hello! I'd like some recommendations",
        "Can you suggest some good restaurants?",
        "What about sightseeing places?",
        "Any events happening nearby?"
    ]
    
    for message in conversation:
        send_message(session_id, message)
        time.sleep(1)  # Small delay for readability
        print()
    
    # Get specific recommendations
    print("\n🎯 Getting Specific Recommendations")
    print("-" * 40)
    
    categories = ["restaurants", "sightseeing", "events"]
    for category in categories:
        get_recommendations(session_id, category)
        print()
    
    # Get chat history
    get_chat_history(session_id)
    
    # Demonstrate multi-language support
    demo_multilingual()
    
    print("\n🎉 Demo completed successfully!")
    print("   You can now integrate this API with your frontend application.")

if __name__ == "__main__":
    main()
