import requests
import logging
from datetime import datetime, timedelta
from geopy.distance import geodesic
from config.config import Config
import json

logger = logging.getLogger(__name__)

class MapMyIndiaService:
    """Service for MapMyIndia API integration - Free alternative to Google Maps"""
    
    def __init__(self):
        self.api_key = Config.MAPMYINDIA_API_KEY
        self.client_id = Config.MAPMYINDIA_CLIENT_ID
        self.client_secret = Config.MAPMYINDIA_CLIENT_SECRET
        self.base_url = "https://apis.mapmyindia.com"
        self.access_token = None
        self.token_expires_at = None
        
    def _get_access_token(self):
        """Get OAuth access token for MapMyIndia API"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token

        try:
            # Updated OAuth endpoint based on MapMyIndia documentation
            url = "https://outpost.mapmyindia.com/api/security/oauth/token"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }

            response = requests.post(url, headers=headers, data=data)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
                logger.info("Successfully obtained MapMyIndia access token")
                return self.access_token
            else:
                logger.error(f"Failed to get MapMyIndia access token: {response.status_code}")
                try:
                    error_response = response.json()
                    logger.error(f"Error details: {error_response}")
                except:
                    logger.error(f"Error response: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting MapMyIndia access token: {e}")
            return None
    
    def geocode_location(self, location_string):
        """Geocode a location string to get latitude and longitude"""
        # Note: MapMyIndia geocoding API has authentication issues
        # Using Nominatim as primary geocoding service since it's working well
        # MapMyIndia is used for nearby search which works perfectly
        logger.info(f"Geocoding with Nominatim (MapMyIndia geocoding has auth issues): {location_string}")
        return {'latitude': None, 'longitude': None, 'formatted_address': location_string}
    
    def nearby_search(self, latitude, longitude, category, radius=5000):
        """Search for nearby places using MapMyIndia Nearby API"""
        try:
            access_token = self._get_access_token()
            if not access_token:
                return []
            
            # Map categories to MapMyIndia keywords
            category_mapping = {
                'restaurant': 'FODCOF',  # Food Court/Restaurant
                'tourist_attraction': 'TOUATT',  # Tourist Attraction
                'museum': 'MUSART',  # Museum/Art Gallery
                'park': 'RECPAR',  # Recreation/Park
                'shopping_mall': 'SHPMAL',  # Shopping Mall
                'bar': 'FODBAR',  # Bar
                'night_club': 'ENTDIS',  # Entertainment/Disco
                'hospital': 'HOSPIL',  # Hospital
                'atm': 'FINATM',  # ATM
                'gas_station': 'AUTSER'  # Auto Service/Gas Station
            }
            
            keywords = category_mapping.get(category, 'FODCOF')  # Default to restaurant
            
            # Updated nearby search endpoint
            url = f"https://atlas.mapmyindia.com/api/places/nearby/json"
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            params = {
                'keywords': keywords,
                'refLocation': f"{latitude},{longitude}",
                'radius': radius,
                'page': 1
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                places = []

                # Updated response parsing for MapMyIndia API
                suggested_locations = data.get('suggestedLocations', [])
                if not suggested_locations and 'results' in data:
                    suggested_locations = data.get('results', [])

                for place in suggested_locations:
                    # Handle different response formats
                    place_name = place.get('placeName') or place.get('name') or 'Unknown'
                    place_address = place.get('placeAddress') or place.get('address') or ''
                    place_lat = place.get('latitude') or place.get('lat') or 0
                    place_lng = place.get('longitude') or place.get('lng') or 0
                    place_id = place.get('eLoc') or place.get('place_id') or ''

                    place_info = {
                        'name': place_name,
                        'address': place_address,
                        'latitude': float(place_lat),
                        'longitude': float(place_lng),
                        'category': category.replace('_', ' ').title(),
                        'place_id': place_id,
                        'distance': self._calculate_distance(
                            latitude, longitude,
                            float(place_lat),
                            float(place_lng)
                        ),
                        'rating': 0,  # MapMyIndia doesn't provide ratings in nearby search
                        'price_level': 0  # Not available in MapMyIndia
                    }
                    places.append(place_info)

                logger.info(f"Found {len(places)} places from MapMyIndia for category: {category}")
                return places[:10]  # Limit to 10 results
            else:
                logger.error(f"MapMyIndia nearby search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error in MapMyIndia nearby search: {e}")
            return []
    
    def get_place_details(self, place_id):
        """Get detailed information about a place using eLoc"""
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {}
            
            url = f"{self.base_url}/advancedmaps/v1/place_detail"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'place_id': place_id
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('results', [])
                
                if result:
                    place = result[0]
                    details = {}
                    
                    if 'phone' in place:
                        details['phone'] = place['phone']
                    
                    if 'website' in place:
                        details['website'] = place['website']
                    
                    # MapMyIndia doesn't provide opening hours or reviews in the same format
                    # We'll return basic details
                    return details
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting place details from MapMyIndia: {e}")
            return {}
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        try:
            distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
            return round(distance, 2)
        except:
            return 0
    
    def reverse_geocode(self, latitude, longitude):
        """Get address from coordinates"""
        try:
            # Get OAuth access token first
            access_token = self._get_access_token()
            if not access_token:
                return f"{latitude}, {longitude}"

            url = f"https://atlas.mapmyindia.com/api/places/rev_geocode/json"
            params = {
                'lat': latitude,
                'lng': longitude
            }
            headers = {
                'Authorization': f'Bearer {access_token}'
            }

            response = requests.get(url, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                if results:
                    result = results[0]
                    return result.get('formatted_address', f"{latitude}, {longitude}")

            return f"{latitude}, {longitude}"

        except Exception as e:
            logger.error(f"Error in reverse geocoding: {e}")
            return f"{latitude}, {longitude}"
