import requests
import logging
from datetime import datetime, timedelta
from geopy.distance import geodesic
from config.config import Config
from config.database import get_redis_client
from chatbot.models import Recommendation, db
import json

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Engine for fetching location-based recommendations"""
    
    def __init__(self):
        self.google_api_key = Config.GOOGLE_PLACES_API_KEY
        self.foursquare_api_key = Config.FOURSQUARE_API_KEY
        self.redis_client = get_redis_client()
        self.radius = Config.RECOMMENDATION_RADIUS
        self.max_results = Config.MAX_RECOMMENDATIONS_PER_CATEGORY
    
    def get_recommendations(self, latitude, longitude, category, language='en'):
        """Get recommendations for a specific location and category"""
        location_key = f"{latitude}_{longitude}_{category}_{language}"
        
        # Check cache first
        cached_recommendations = self._get_cached_recommendations(location_key, language)
        if cached_recommendations:
            return cached_recommendations
        
        # Fetch fresh recommendations
        recommendations = []
        
        if category == 'restaurants':
            recommendations = self._get_restaurant_recommendations(latitude, longitude)
        elif category == 'sightseeing':
            recommendations = self._get_sightseeing_recommendations(latitude, longitude)
        elif category == 'events':
            recommendations = self._get_event_recommendations(latitude, longitude)
        elif category == 'shopping':
            recommendations = self._get_shopping_recommendations(latitude, longitude)
        elif category == 'nightlife':
            recommendations = self._get_nightlife_recommendations(latitude, longitude)
        
        # Cache the recommendations
        self._cache_recommendations(location_key, recommendations, language)
        
        return recommendations
    
    def _get_restaurant_recommendations(self, latitude, longitude):
        """Get restaurant recommendations using Google Places API"""
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{latitude},{longitude}",
                'radius': self.radius,
                'type': 'restaurant',
                'key': self.google_api_key,
                'fields': 'name,rating,price_level,vicinity,photos,place_id'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            restaurants = []
            for place in data.get('results', [])[:self.max_results]:
                restaurant = {
                    'name': place.get('name'),
                    'rating': place.get('rating', 0),
                    'price_level': place.get('price_level', 0),
                    'address': place.get('vicinity'),
                    'place_id': place.get('place_id'),
                    'category': 'Restaurant',
                    'distance': self._calculate_distance(
                        latitude, longitude,
                        place['geometry']['location']['lat'],
                        place['geometry']['location']['lng']
                    )
                }
                
                # Get additional details
                details = self._get_place_details(place.get('place_id'))
                if details:
                    restaurant.update(details)
                
                restaurants.append(restaurant)
            
            return sorted(restaurants, key=lambda x: x.get('rating', 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Error fetching restaurant recommendations: {e}")
            return []
    
    def _get_sightseeing_recommendations(self, latitude, longitude):
        """Get sightseeing recommendations"""
        try:
            attractions = []
            
            # Get tourist attractions
            for place_type in ['tourist_attraction', 'museum', 'park', 'zoo']:
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    'location': f"{latitude},{longitude}",
                    'radius': self.radius,
                    'type': place_type,
                    'key': self.google_api_key
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                for place in data.get('results', []):
                    attraction = {
                        'name': place.get('name'),
                        'rating': place.get('rating', 0),
                        'address': place.get('vicinity'),
                        'place_id': place.get('place_id'),
                        'category': place_type.replace('_', ' ').title(),
                        'distance': self._calculate_distance(
                            latitude, longitude,
                            place['geometry']['location']['lat'],
                            place['geometry']['location']['lng']
                        )
                    }
                    
                    # Get additional details
                    details = self._get_place_details(place.get('place_id'))
                    if details:
                        attraction.update(details)
                    
                    attractions.append(attraction)
            
            # Remove duplicates and sort by rating
            unique_attractions = {attr['place_id']: attr for attr in attractions}.values()
            return sorted(list(unique_attractions), key=lambda x: x.get('rating', 0), reverse=True)[:self.max_results]
            
        except Exception as e:
            logger.error(f"Error fetching sightseeing recommendations: {e}")
            return []
    
    def _get_event_recommendations(self, latitude, longitude):
        """Get event recommendations (placeholder - integrate with event APIs)"""
        # This would integrate with event APIs like Eventbrite, Meetup, etc.
        # For now, returning sample data
        return [
            {
                'name': 'Local Cultural Festival',
                'category': 'Cultural Event',
                'date': '2024-01-15',
                'time': '18:00',
                'address': 'City Center',
                'description': 'Experience local culture and traditions',
                'rating': 4.5,
                'distance': 2.1
            },
            {
                'name': 'Live Music Concert',
                'category': 'Music Event',
                'date': '2024-01-16',
                'time': '20:00',
                'address': 'Music Hall',
                'description': 'Local and international artists',
                'rating': 4.3,
                'distance': 1.8
            }
        ]
    
    def _get_shopping_recommendations(self, latitude, longitude):
        """Get shopping recommendations"""
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{latitude},{longitude}",
                'radius': self.radius,
                'type': 'shopping_mall',
                'key': self.google_api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            shopping_places = []
            for place in data.get('results', [])[:self.max_results]:
                shop = {
                    'name': place.get('name'),
                    'rating': place.get('rating', 0),
                    'address': place.get('vicinity'),
                    'place_id': place.get('place_id'),
                    'category': 'Shopping',
                    'distance': self._calculate_distance(
                        latitude, longitude,
                        place['geometry']['location']['lat'],
                        place['geometry']['location']['lng']
                    )
                }
                
                details = self._get_place_details(place.get('place_id'))
                if details:
                    shop.update(details)
                
                shopping_places.append(shop)
            
            return sorted(shopping_places, key=lambda x: x.get('rating', 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Error fetching shopping recommendations: {e}")
            return []
    
    def _get_nightlife_recommendations(self, latitude, longitude):
        """Get nightlife recommendations"""
        try:
            nightlife_places = []
            
            for place_type in ['bar', 'night_club', 'casino']:
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    'location': f"{latitude},{longitude}",
                    'radius': self.radius,
                    'type': place_type,
                    'key': self.google_api_key
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                for place in data.get('results', []):
                    nightlife = {
                        'name': place.get('name'),
                        'rating': place.get('rating', 0),
                        'address': place.get('vicinity'),
                        'place_id': place.get('place_id'),
                        'category': place_type.replace('_', ' ').title(),
                        'distance': self._calculate_distance(
                            latitude, longitude,
                            place['geometry']['location']['lat'],
                            place['geometry']['location']['lng']
                        )
                    }
                    
                    details = self._get_place_details(place.get('place_id'))
                    if details:
                        nightlife.update(details)
                    
                    nightlife_places.append(nightlife)
            
            unique_places = {place['place_id']: place for place in nightlife_places}.values()
            return sorted(list(unique_places), key=lambda x: x.get('rating', 0), reverse=True)[:self.max_results]
            
        except Exception as e:
            logger.error(f"Error fetching nightlife recommendations: {e}")
            return []
    
    def _get_place_details(self, place_id):
        """Get additional details for a place"""
        if not place_id:
            return {}
        
        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                'place_id': place_id,
                'fields': 'formatted_phone_number,website,opening_hours,reviews',
                'key': self.google_api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            result = data.get('result', {})
            details = {}
            
            if 'formatted_phone_number' in result:
                details['phone'] = result['formatted_phone_number']
            
            if 'website' in result:
                details['website'] = result['website']
            
            if 'opening_hours' in result:
                details['opening_hours'] = result['opening_hours'].get('weekday_text', [])
            
            if 'reviews' in result:
                reviews = [review['text'] for review in result['reviews'][:3]]
                details['reviews'] = reviews
            
            return details
            
        except Exception as e:
            logger.error(f"Error fetching place details: {e}")
            return {}
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        try:
            distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
            return round(distance, 2)
        except:
            return 0
    
    def _get_cached_recommendations(self, location_key, language):
        """Get recommendations from cache"""
        try:
            # Check Redis cache first
            cache_key = f"recommendations:{location_key}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            # Check database cache
            recommendation = Recommendation.query.filter_by(
                location_key=location_key,
                language=language
            ).first()
            
            if recommendation and not recommendation.is_expired():
                # Update Redis cache
                self.redis_client.setex(
                    cache_key, 
                    Config.CACHE_TIMEOUT, 
                    json.dumps(recommendation.data)
                )
                return recommendation.data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached recommendations: {e}")
            return None
    
    def _cache_recommendations(self, location_key, recommendations, language):
        """Cache recommendations"""
        try:
            # Cache in Redis
            cache_key = f"recommendations:{location_key}"
            self.redis_client.setex(
                cache_key, 
                Config.CACHE_TIMEOUT, 
                json.dumps(recommendations)
            )
            
            # Cache in database
            expires_at = datetime.utcnow() + timedelta(seconds=Config.CACHE_TIMEOUT)
            
            # Remove old cache entry if exists
            old_recommendation = Recommendation.query.filter_by(
                location_key=location_key,
                language=language
            ).first()
            
            if old_recommendation:
                db.session.delete(old_recommendation)
            
            # Create new cache entry
            recommendation = Recommendation(
                location_key=location_key,
                category=location_key.split('_')[2],  # Extract category from key
                data=recommendations,
                language=language,
                expires_at=expires_at
            )
            
            db.session.add(recommendation)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error caching recommendations: {e}")
