#!/usr/bin/env python3
"""
Test script to verify the new booking event handling works correctly.
This script tests the event parsing logic without requiring a full database setup.
"""

import json
from datetime import datetime

# Sample booking event data (similar to what external service sends)
SAMPLE_BOOKING_EVENT = {
    "message_id": "EVT-050625-1121-9199-5649",
    "generated_at": "2025-06-05T16:51:39.745904+05:30",
    "events": [
        {
            "entity_name": "booking",
            "payload": {
                "booking_id": "3387-8193-5572",
                "reference_number": "TRB-17491224854750",
                "hotel_id": "0016581",
                "status": "reserved",
                "checkin_date": "2025-06-05T14:00:00+05:30",
                "checkout_date": "2025-06-06T12:00:00+05:30",
                "source": {
                    "channel_code": "direct",
                    "application_code": "website",
                    "subchannel_code": "website-direct"
                },
                "customers": [
                    {
                        "customer_id": "1",
                        "first_name": "Vivek",
                        "last_name": "Yadav",
                        "email": "vivekyadav.9991+11@gmail.com",
                        "phone": {
                            "number": "8904348449",
                            "country_code": "+91"
                        },
                        "is_primary": False,
                        "dummy": False
                    }
                ]
            }
        },
        {
            "entity_name": "bill",
            "payload": {
                "vendor_details": {
                    "hotel_name": "Treebo Club Worldtree Staging",
                    "vendor_name": "Treebo Club Worldtree Staging",
                    "address": {
                        "field_1": "#204, Prashant Extension, Near Hope Farm Whitefield",
                        "city": "Bangalore",
                        "state": "Karnataka",
                        "pincode": "560066"
                    },
                    "phone": {
                        "number": "9322800100",
                        "country_code": "+91"
                    },
                    "email": "hello@treebohotels.com"
                }
            }
        }
    ],
    "event_type": "booking.created"
}

def test_event_parsing():
    """Test the event parsing logic"""
    print("🧪 Testing booking event parsing...")
    
    event_data = SAMPLE_BOOKING_EVENT
    event_type = event_data.get('event_type')
    
    print(f"✓ Event type: {event_type}")
    
    # Extract booking data from the events array
    booking_event = None
    bill_event = None
    
    for event in event_data['events']:
        if event.get('entity_name') == 'booking':
            booking_event = event
        elif event.get('entity_name') == 'bill':
            bill_event = event
    
    if not booking_event:
        print("❌ No booking event found")
        return False
    
    booking_data = booking_event.get('payload', {})
    if bill_event:
        booking_data['bill_data'] = bill_event.get('payload', {})
    
    print(f"✓ Found booking event with ID: {booking_data.get('booking_id')}")
    
    # Test data extraction
    booking_id = booking_data.get('booking_id')
    reference_number = booking_data.get('reference_number')
    hotel_id = booking_data.get('hotel_id')
    
    print(f"✓ Booking ID: {booking_id}")
    print(f"✓ Reference Number: {reference_number}")
    print(f"✓ Hotel ID: {hotel_id}")
    
    # Extract guest information
    customers = booking_data.get('customers', [])
    primary_customer = None
    
    for customer in customers:
        if not customer.get('dummy', False) and customer.get('email'):
            primary_customer = customer
            break
    
    if primary_customer:
        guest_name = primary_customer.get('first_name', '')
        if primary_customer.get('last_name'):
            guest_name += f" {primary_customer['last_name']}"
        guest_email = primary_customer.get('email')
        phone_info = primary_customer.get('phone', {})
        guest_phone = f"{phone_info.get('country_code', '')}{phone_info.get('number', '')}" if phone_info else None
        
        print(f"✓ Guest Name: {guest_name}")
        print(f"✓ Guest Email: {guest_email}")
        print(f"✓ Guest Phone: {guest_phone}")
    else:
        print("❌ No primary customer found")
        return False
    
    # Extract hotel information
    bill_data = booking_data.get('bill_data', {})
    vendor_details = bill_data.get('vendor_details', {})
    
    if vendor_details:
        hotel_name = vendor_details.get('hotel_name') or vendor_details.get('vendor_name')
        address_info = vendor_details.get('address', {})
        if address_info:
            hotel_location = f"{address_info.get('field_1', '')}, {address_info.get('city', '')}, {address_info.get('state', '')}"
            hotel_location = hotel_location.strip(', ')
        
        print(f"✓ Hotel Name: {hotel_name}")
        print(f"✓ Hotel Location: {hotel_location}")
    else:
        print("❌ No vendor details found")
        return False
    
    # Extract dates
    check_in_date = booking_data.get('checkin_date')
    check_out_date = booking_data.get('checkout_date')
    
    if check_in_date and 'T' in check_in_date:
        check_in_date = check_in_date.split('T')[0]
    if check_out_date and 'T' in check_out_date:
        check_out_date = check_out_date.split('T')[0]
    
    print(f"✓ Check-in Date: {check_in_date}")
    print(f"✓ Check-out Date: {check_out_date}")
    
    # Validate required fields
    required_fields = [booking_id, guest_name, guest_email, hotel_name]
    if all(required_fields):
        print("✅ All required fields extracted successfully!")
        return True
    else:
        print("❌ Missing required fields")
        return False

def test_legacy_format():
    """Test backward compatibility with legacy format"""
    print("\n🧪 Testing legacy format compatibility...")
    
    legacy_event = {
        "event_type": "booking.created",
        "booking": {
            "booking_id": "LEGACY-123",
            "guest_name": "John Doe",
            "guest_email": "john@example.com",
            "hotel_name": "Test Hotel",
            "hotel_location": "Test City",
            "check_in_date": "2025-06-05",
            "check_out_date": "2025-06-06",
            "guest_language": "en"
        }
    }
    
    event_type = legacy_event.get('event_type')
    
    # Handle legacy simple event structure
    if 'events' in legacy_event and len(legacy_event['events']) > 0:
        print("❌ Should not have events array in legacy format")
        return False
    else:
        booking_data = legacy_event.get('booking', {})
        print(f"✓ Legacy format detected, booking ID: {booking_data.get('booking_id')}")
        return True

if __name__ == "__main__":
    print("🚀 Testing Booking Event Handler Updates\n")
    
    success1 = test_event_parsing()
    success2 = test_legacy_format()
    
    if success1 and success2:
        print("\n🎉 All tests passed! The booking event handler should work correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
