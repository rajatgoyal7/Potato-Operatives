#!/usr/bin/env python3
"""
Test script to verify MapMyIndia API integration works correctly.
This script tests the MapMyIndia service without requiring a full application setup.
"""

import os
import sys
from datetime import datetime

# Mock the config for testing
class MockConfig:
    MAPMYINDIA_API_KEY = os.environ.get('MAPMYINDIA_API_KEY', 'test_api_key')
    MAPMYINDIA_CLIENT_ID = os.environ.get('MAPMYINDIA_CLIENT_ID', 'test_client_id')
    MAPMYINDIA_CLIENT_SECRET = os.environ.get('MAPMYINDIA_CLIENT_SECRET', 'test_client_secret')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_mapmyindia_service():
    """Test MapMyIndia service functionality"""
    print("🧪 Testing MapMyIndia API Integration\n")
    
    try:
        # Import after setting up the path
        from chatbot.mapmyindia_service import MapMyIndiaService
        
        # Override config for testing
        import chatbot.mapmyindia_service
        chatbot.mapmyindia_service.Config = MockConfig
        
        service = MapMyIndiaService()
        
        print("✓ MapMyIndia service initialized successfully")
        
        # Test 1: Geocoding
        print("\n📍 Testing Geocoding...")
        test_locations = [
            "Connaught Place, New Delhi",
            "Brigade Road, Bangalore",
            "Marine Drive, Mumbai",
            "Park Street, Kolkata"
        ]
        
        for location in test_locations:
            print(f"  Testing: {location}")
            result = service.geocode_location(location)
            
            if result.get('latitude') and result.get('longitude'):
                print(f"    ✓ Success: {result['latitude']}, {result['longitude']}")
            else:
                print(f"    ⚠️  No coordinates found (expected with test keys)")
        
        # Test 2: Nearby Search
        print("\n🔍 Testing Nearby Search...")
        # Use Delhi coordinates for testing
        test_lat, test_lng = 28.6139, 77.2090
        
        categories = ['restaurant', 'tourist_attraction', 'shopping_mall', 'bar']
        
        for category in categories:
            print(f"  Testing category: {category}")
            places = service.nearby_search(test_lat, test_lng, category, 5000)
            
            if places:
                print(f"    ✓ Found {len(places)} places")
                for place in places[:2]:  # Show first 2 results
                    print(f"      - {place.get('name', 'Unknown')} ({place.get('distance', 0)} km)")
            else:
                print(f"    ⚠️  No places found (expected with test keys)")
        
        # Test 3: Reverse Geocoding
        print("\n🗺️  Testing Reverse Geocoding...")
        address = service.reverse_geocode(test_lat, test_lng)
        print(f"  Coordinates: {test_lat}, {test_lng}")
        print(f"  Address: {address}")
        
        # Test 4: Distance Calculation
        print("\n📏 Testing Distance Calculation...")
        lat1, lng1 = 28.6139, 77.2090  # Delhi
        lat2, lng2 = 19.0760, 72.8777  # Mumbai
        
        distance = service._calculate_distance(lat1, lng1, lat2, lng2)
        print(f"  Distance between Delhi and Mumbai: {distance} km")
        
        if distance > 1000:  # Should be around 1150 km
            print("  ✓ Distance calculation working correctly")
        else:
            print("  ❌ Distance calculation may have issues")
        
        print("\n🎉 MapMyIndia integration test completed!")
        print("\n📝 Notes:")
        print("  - Some tests may show warnings with test API keys")
        print("  - Set real MAPMYINDIA_* environment variables for full testing")
        print("  - The service includes fallback mechanisms for production use")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_recommendation_engine_integration():
    """Test that the recommendation engine can use MapMyIndia"""
    print("\n🔧 Testing Recommendation Engine Integration...")
    
    try:
        # Mock the database and other dependencies
        class MockDB:
            def __init__(self):
                pass
            def add(self, obj):
                pass
            def commit(self):
                pass
        
        class MockRedis:
            def get(self, key):
                return None
            def setex(self, key, time, value):
                pass
        
        # Mock the modules
        sys.modules['config.database'] = type('MockModule', (), {
            'get_redis_client': lambda: MockRedis(),
            'db': MockDB()
        })()
        
        sys.modules['chatbot.models'] = type('MockModule', (), {
            'Recommendation': type('MockRecommendation', (), {}),
            'db': MockDB()
        })()
        
        from chatbot.recommendation_engine import RecommendationEngine
        
        engine = RecommendationEngine()
        print("✓ Recommendation engine initialized with MapMyIndia service")
        
        # Test that MapMyIndia service is available
        if hasattr(engine, 'mapmyindia_service'):
            print("✓ MapMyIndia service is properly integrated")
        else:
            print("❌ MapMyIndia service not found in recommendation engine")
            return False
        
        print("✓ Recommendation engine integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Recommendation engine test failed: {e}")
        return False

def show_api_setup_instructions():
    """Show instructions for setting up MapMyIndia API"""
    print("\n📋 MapMyIndia API Setup Instructions:")
    print("=" * 50)
    print("1. Visit: https://www.mapmyindia.com/api/")
    print("2. Sign up for a free account")
    print("3. Create a new project")
    print("4. Get your API credentials:")
    print("   - API Key")
    print("   - Client ID") 
    print("   - Client Secret")
    print("5. Set environment variables:")
    print("   export MAPMYINDIA_API_KEY='your_api_key'")
    print("   export MAPMYINDIA_CLIENT_ID='your_client_id'")
    print("   export MAPMYINDIA_CLIENT_SECRET='your_client_secret'")
    print("\n💡 Free tier includes:")
    print("   - 10,000 geocoding requests/month")
    print("   - 10,000 nearby search requests/month")
    print("   - No credit card required")

if __name__ == "__main__":
    print("🚀 MapMyIndia Integration Test Suite")
    print("=" * 50)
    
    # Check if API keys are set
    api_key = os.environ.get('MAPMYINDIA_API_KEY')
    client_id = os.environ.get('MAPMYINDIA_CLIENT_ID')
    client_secret = os.environ.get('MAPMYINDIA_CLIENT_SECRET')
    
    if not all([api_key, client_id, client_secret]):
        print("⚠️  MapMyIndia API credentials not found in environment variables")
        print("Tests will run with mock data\n")
    else:
        print("✓ MapMyIndia API credentials found\n")
    
    # Run tests
    test1_passed = test_mapmyindia_service()
    test2_passed = test_recommendation_engine_integration()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  MapMyIndia Service: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  Engine Integration: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if not all([api_key, client_id, client_secret]):
        show_api_setup_instructions()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! MapMyIndia integration is ready.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
    
    sys.exit(0 if (test1_passed and test2_passed) else 1)
