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
    """Engine for fetching location-based recommendations using Google Places API"""

    def __init__(self):
        self.google_api_key = Config.GOOGLE_PLACES_API_KEY
        self.redis_client = get_redis_client()
        self.radius = Config.RECOMMENDATION_RADIUS
        self.max_results = Config.MAX_RECOMMENDATIONS_PER_CATEGORY
    
    def get_recommendations(self, latitude, longitude, category, language='en'):
        """Get recommendations for a specific location and category"""
        logger.info(f"Getting {category} recommendations for location: {latitude}, {longitude}")

        # Validate coordinates
        if latitude is None or longitude is None:
            logger.warning(f"Invalid coordinates for recommendations: lat={latitude}, lng={longitude}")
            return []

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
        elif category == 'shopping':
            recommendations = self._get_shopping_recommendations(latitude, longitude)
        elif category == 'nightlife':
            recommendations = self._get_nightlife_recommendations(latitude, longitude)
        elif category == 'atms':
            recommendations = self._get_atm_recommendations(latitude, longitude)
        elif category == 'pharmacy':
            recommendations = self._get_pharmacy_recommendations(latitude, longitude)
        elif category == 'rentals':
            recommendations = self._get_rental_recommendations(latitude, longitude)
        
        # Cache the recommendations
        self._cache_recommendations(location_key, recommendations, language)
        
        return recommendations
    
    def _get_restaurant_recommendations(self, latitude, longitude):
        """Get restaurant recommendations using Google Places API"""
        if not self.google_api_key:
            logger.error("Google Places API key not configured")
            return []

        return self._get_restaurant_recommendations_google(latitude, longitude)

    def _get_restaurant_recommendations_google(self, latitude, longitude):
        """Fallback method using Google Places API"""
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
                    'latitude': place['geometry']['location']['lat'],
                    'longitude': place['geometry']['location']['lng'],
                    'distance': self._calculate_distance(
                        latitude, longitude,
                        place['geometry']['location']['lat'],
                        place['geometry']['location']['lng']
                    )
                }

                # Get additional details
                details = self._get_place_details_google(place.get('place_id'))
                if details:
                    restaurant.update(details)

                # Enhance with additional details and maps link
                restaurant = self._enhance_place_with_details(restaurant, 'restaurants')

                restaurants.append(restaurant)

            return sorted(restaurants, key=lambda x: x.get('rating', 0), reverse=True)

        except Exception as e:
            logger.error(f"Error fetching restaurant recommendations from Google: {e}")
            return []
    
    def _get_sightseeing_recommendations(self, latitude, longitude):
        """Get sightseeing recommendations using Google Places API"""
        if not self.google_api_key:
            logger.error("Google Places API key not configured")
            return []

        return self._get_sightseeing_recommendations_google(latitude, longitude)

    def _get_sightseeing_recommendations_google(self, latitude, longitude):
        """Fallback method for sightseeing using Google Places API"""
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
                        'latitude': place['geometry']['location']['lat'],
                        'longitude': place['geometry']['location']['lng'],
                        'distance': self._calculate_distance(
                            latitude, longitude,
                            place['geometry']['location']['lat'],
                            place['geometry']['location']['lng']
                        )
                    }

                    # Get additional details
                    details = self._get_place_details_google(place.get('place_id'))
                    if details:
                        attraction.update(details)

                    # Enhance with additional details and maps link
                    attraction = self._enhance_place_with_details(attraction, 'sightseeing')

                    attractions.append(attraction)

            # Remove duplicates and sort by rating
            unique_attractions = {attr['place_id']: attr for attr in attractions}.values()
            return sorted(list(unique_attractions), key=lambda x: x.get('rating', 0), reverse=True)[:self.max_results]

        except Exception as e:
            logger.error(f"Error fetching sightseeing recommendations from Google: {e}")
            return []
    

    
    def _get_shopping_recommendations(self, latitude, longitude):
        """Get shopping recommendations using Google Places API"""
        if not self.google_api_key:
            logger.error("Google Places API key not configured")
            return []

        return self._get_shopping_recommendations_google(latitude, longitude)

    def _get_shopping_recommendations_google(self, latitude, longitude):
        """Get shopping recommendations using Google Places API"""
        try:
            shopping_places = []

            # Search for different types of shopping places
            for place_type in ['shopping_mall', 'store', 'clothing_store', 'electronics_store', 'department_store']:
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
                    shop = {
                        'name': place.get('name'),
                        'rating': place.get('rating', 0),
                        'address': place.get('vicinity'),
                        'place_id': place.get('place_id'),
                        'category': place_type.replace('_', ' ').title(),
                        'latitude': place['geometry']['location']['lat'],
                        'longitude': place['geometry']['location']['lng'],
                        'distance': self._calculate_distance(
                            latitude, longitude,
                            place['geometry']['location']['lat'],
                            place['geometry']['location']['lng']
                        )
                    }

                    details = self._get_place_details_google(place.get('place_id'))
                    if details:
                        shop.update(details)

                    # Enhance with additional details and maps link
                    shop = self._enhance_place_with_details(shop, 'shopping')

                    shopping_places.append(shop)

            # Remove duplicates and sort by rating
            unique_places = {place['place_id']: place for place in shopping_places if place.get('place_id')}.values()
            return sorted(list(unique_places), key=lambda x: x.get('rating', 0), reverse=True)[:self.max_results]

        except Exception as e:
            logger.error(f"Error fetching shopping recommendations from Google: {e}")
            return []
    
    def _get_nightlife_recommendations(self, latitude, longitude):
        """Get nightlife recommendations using Google Places API"""
        if not self.google_api_key:
            logger.error("Google Places API key not configured")
            return []

        return self._get_nightlife_recommendations_google(latitude, longitude)

    def _get_nightlife_recommendations_google(self, latitude, longitude):
        """Fallback method for nightlife using Google Places API"""
        try:
            nightlife_places = []

            for place_type in ['bar', 'night_club', 'casino', 'bowling_alley']:
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
                        'latitude': place['geometry']['location']['lat'],
                        'longitude': place['geometry']['location']['lng'],
                        'distance': self._calculate_distance(
                            latitude, longitude,
                            place['geometry']['location']['lat'],
                            place['geometry']['location']['lng']
                        )
                    }

                    details = self._get_place_details_google(place.get('place_id'))
                    if details:
                        nightlife.update(details)

                    # Enhance with additional details and maps link
                    nightlife = self._enhance_place_with_details(nightlife, 'nightlife')

                    nightlife_places.append(nightlife)

            unique_places = {place['place_id']: place for place in nightlife_places}.values()
            return sorted(list(unique_places), key=lambda x: x.get('rating', 0), reverse=True)[:self.max_results]

        except Exception as e:
            logger.error(f"Error fetching nightlife recommendations from Google: {e}")
            return []

    def _get_atm_recommendations(self, latitude, longitude):
        """Get ATM recommendations using Google Places API"""
        if not self.google_api_key:
            logger.error("Google Places API key not configured")
            return []

        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{latitude},{longitude}",
                'radius': self.radius,
                'type': 'atm',
                'key': self.google_api_key
            }

            response = requests.get(url, params=params)
            data = response.json()

            atms = []
            for place in data.get('results', [])[:self.max_results]:
                atm = {
                    'name': place.get('name'),
                    'rating': place.get('rating', 0),
                    'address': place.get('vicinity'),
                    'place_id': place.get('place_id'),
                    'category': 'ATM',
                    'latitude': place['geometry']['location']['lat'],
                    'longitude': place['geometry']['location']['lng'],
                    'distance': self._calculate_distance(
                        latitude, longitude,
                        place['geometry']['location']['lat'],
                        place['geometry']['location']['lng']
                    )
                }

                details = self._get_place_details_google(place.get('place_id'))
                if details:
                    atm.update(details)

                # Enhance with additional details and maps link
                atm = self._enhance_place_with_details(atm, 'atms')

                atms.append(atm)

            return sorted(atms, key=lambda x: x.get('distance', 999))

        except Exception as e:
            logger.error(f"Error fetching ATM recommendations from Google: {e}")
            return []

    def _get_pharmacy_recommendations(self, latitude, longitude):
        """Get pharmacy recommendations using Google Places API"""
        if not self.google_api_key:
            logger.error("Google Places API key not configured")
            return []

        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{latitude},{longitude}",
                'radius': self.radius,
                'type': 'pharmacy',
                'key': self.google_api_key
            }

            response = requests.get(url, params=params)
            data = response.json()

            pharmacies = []
            for place in data.get('results', [])[:self.max_results]:
                pharmacy = {
                    'name': place.get('name'),
                    'rating': place.get('rating', 0),
                    'address': place.get('vicinity'),
                    'place_id': place.get('place_id'),
                    'category': 'Pharmacy',
                    'latitude': place['geometry']['location']['lat'],
                    'longitude': place['geometry']['location']['lng'],
                    'distance': self._calculate_distance(
                        latitude, longitude,
                        place['geometry']['location']['lat'],
                        place['geometry']['location']['lng']
                    )
                }

                details = self._get_place_details_google(place.get('place_id'))
                if details:
                    pharmacy.update(details)

                # Enhance with additional details and maps link
                pharmacy = self._enhance_place_with_details(pharmacy, 'pharmacy')

                pharmacies.append(pharmacy)

            return sorted(pharmacies, key=lambda x: x.get('distance', 999))

        except Exception as e:
            logger.error(f"Error fetching pharmacy recommendations from Google: {e}")
            return []

    def _get_rental_recommendations(self, latitude, longitude):
        """Get rental service recommendations using Google Places API"""
        if not self.google_api_key:
            logger.error("Google Places API key not configured")
            return []

        try:
            rentals = []

            # Search for car rental and bike rental services
            for rental_type in ['car_rental', 'bicycle_store']:
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    'location': f"{latitude},{longitude}",
                    'radius': self.radius,
                    'type': rental_type,
                    'key': self.google_api_key
                }

                response = requests.get(url, params=params)
                data = response.json()

                for place in data.get('results', []):
                    rental = {
                        'name': place.get('name'),
                        'rating': place.get('rating', 0),
                        'address': place.get('vicinity'),
                        'place_id': place.get('place_id'),
                        'category': 'Rental Service',
                        'latitude': place['geometry']['location']['lat'],
                        'longitude': place['geometry']['location']['lng'],
                        'distance': self._calculate_distance(
                            latitude, longitude,
                            place['geometry']['location']['lat'],
                            place['geometry']['location']['lng']
                        )
                    }

                    details = self._get_place_details_google(place.get('place_id'))
                    if details:
                        rental.update(details)

                    # Enhance with additional details and maps link
                    rental = self._enhance_place_with_details(rental, 'rentals')

                    rentals.append(rental)

            # Remove duplicates and sort by distance
            unique_rentals = {rental['place_id']: rental for rental in rentals if rental.get('place_id')}.values()
            return sorted(list(unique_rentals), key=lambda x: x.get('distance', 999))[:self.max_results]

        except Exception as e:
            logger.error(f"Error fetching rental recommendations from Google: {e}")
            return []

    def _get_place_details_google(self, place_id):
        """Get additional details for a place using Google Places API"""
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
            logger.error(f"Error fetching place details from Google: {e}")
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

    def _enhance_place_with_details(self, place, category):
        """Enhance place details with additional info and maps link"""
        try:
            # Add estimated pricing based on category and rating
            place['estimated_pricing'] = self._estimate_pricing(category, place.get('rating', 0))

            # Add visit duration estimate
            place['visit_duration'] = self._estimate_visit_duration(category)

            # Add best time to visit
            place['best_time'] = self._get_best_time_to_visit(category)

            # Add Google Maps link if coordinates are available
            if place.get('latitude') and place.get('longitude'):
                place['maps_link'] = f"https://www.google.com/maps/search/?api=1&query={place['latitude']},{place['longitude']}"

            return place

        except Exception as e:
            logger.error(f"Error enhancing place with details: {e}")
            return place

    def _estimate_pricing(self, category, rating):
        """Estimate pricing based on category and rating"""
        pricing_map = {
            'restaurants': {
                'base': '₹₹',
                'high_rating': '₹₹₹' if rating >= 4.0 else '₹₹'
            },
            'sightseeing': {
                'base': '₹50-200',
                'high_rating': '₹100-500' if rating >= 4.0 else '₹50-200'
            },
            'shopping': {
                'base': 'Varies',
                'high_rating': 'Premium' if rating >= 4.0 else 'Varies'
            },
            'nightlife': {
                'base': '₹₹₹',
                'high_rating': '₹₹₹₹' if rating >= 4.0 else '₹₹₹'
            },
            'atms': {
                'base': 'Free',
                'high_rating': 'Free'
            },
            'pharmacy': {
                'base': 'Medicines',
                'high_rating': 'Medicines'
            },
            'rentals': {
                'base': '₹500-2000/day',
                'high_rating': '₹1000-3000/day' if rating >= 4.0 else '₹500-2000/day'
            }
        }

        category_pricing = pricing_map.get(category, {'base': 'Varies', 'high_rating': 'Varies'})
        return category_pricing['high_rating'] if rating >= 4.0 else category_pricing['base']

    def _estimate_visit_duration(self, category):
        """Estimate visit duration based on category"""
        duration_map = {
            'restaurants': '1-2 hours',
            'sightseeing': '2-4 hours',
            'shopping': '1-3 hours',
            'nightlife': '2-5 hours',
            'atms': '5 minutes',
            'pharmacy': '10-15 minutes',
            'rentals': '30 minutes'
        }
        return duration_map.get(category, '1-2 hours')

    def _get_best_time_to_visit(self, category):
        """Get best time to visit based on category"""
        time_map = {
            'restaurants': 'Lunch: 12-2 PM, Dinner: 7-10 PM',
            'sightseeing': 'Morning: 9 AM-12 PM, Evening: 4-7 PM',
            'shopping': 'Afternoon: 2-8 PM',
            'nightlife': 'Evening: 8 PM-2 AM',
            'atms': '24/7 Available',
            'pharmacy': 'Daytime: 9 AM-9 PM',
            'rentals': 'Morning: 9 AM-6 PM'
        }
        return time_map.get(category, 'Anytime')
