import logging
import json
from datetime import datetime
from typing import Dict, List
from chatbot.models import Booking, db
from chatbot.chatbot_service import ChatbotService
from chatbot.translation_service import TranslationService

from chatbot.booking_search_service import BookingSearchService
from geopy.geocoders import Nominatim
import hashlib
import hmac

logger = logging.getLogger(__name__)

class EventHandler:
    """Handler for processing booking events"""

    def __init__(self):
        self.chatbot_service = ChatbotService()
        self.translation_service = TranslationService()
        self.booking_search_service = BookingSearchService()
        # Use Nominatim for geocoding
        self.geocoder = Nominatim(user_agent="treebo-chatbot")
    
    def verify_webhook_signature(self, payload, signature, secret):
        """Verify webhook signature for security"""
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def process_booking_event(self, event_data):
        """Process incoming booking event"""
        try:
            event_type = event_data.get('event_type')

            # Handle new complex event structure from external service
            if 'events' in event_data and len(event_data['events']) > 0:
                # Extract booking data from the events array
                booking_event = None
                bill_event = None

                for event in event_data['events']:
                    if event.get('entity_name') == 'booking':
                        booking_event = event
                    elif event.get('entity_name') == 'bill':
                        bill_event = event

                if booking_event:
                    booking_data = booking_event.get('payload', {})
                    # Add bill data if available
                    if bill_event:
                        booking_data['bill_data'] = bill_event.get('payload', {})
                else:
                    logger.error("No booking event found in events array")
                    return {'status': 'error', 'message': 'No booking event found'}
            else:
                # Handle legacy simple event structure for backward compatibility
                booking_data = event_data.get('booking', {})

            if event_type == 'booking.created':
                return self._handle_booking_created(booking_data)
            elif event_type == 'booking.updated':
                return self._handle_booking_updated(booking_data)
            elif event_type == 'booking.cancelled':
                return self._handle_booking_cancelled(booking_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return {'status': 'ignored', 'message': f'Unknown event type: {event_type}'}

        except Exception as e:
            logger.error(f"Error processing booking event: {e}")
            raise
    
    def _handle_booking_created(self, booking_data):
        """Handle new booking creation"""
        try:
            # Extract booking information from complex event structure
            booking_id = booking_data.get('booking_id')
            reference_number = booking_data.get('reference_number')
            hotel_id = booking_data.get('hotel_id')

            # Extract guest information from customers array
            guest_name = None
            guest_email = None
            guest_phone = None

            customers = booking_data.get('customers', [])
            primary_customer = None

            # Find primary customer (non-dummy customer with email)
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
                if phone_info:
                    guest_phone = f"{phone_info.get('country_code', '')}{phone_info.get('number', '')}"

            # Extract hotel information from bill data if available
            hotel_name = None
            hotel_location = None

            bill_data = booking_data.get('bill_data', {})
            vendor_details = bill_data.get('vendor_details', {})

            if vendor_details:
                hotel_name = vendor_details.get('hotel_name') or vendor_details.get('vendor_name')
                address_info = vendor_details.get('address', {})
                if address_info:
                    hotel_location = f"{address_info.get('field_1', '')}, {address_info.get('city', '')}, {address_info.get('state', '')}"
                    hotel_location = hotel_location.strip(', ')

            # Extract dates
            check_in_date = booking_data.get('checkin_date')
            check_out_date = booking_data.get('checkout_date')

            # Convert ISO datetime to date string if needed
            if check_in_date and 'T' in check_in_date:
                check_in_date = check_in_date.split('T')[0]
            if check_out_date and 'T' in check_out_date:
                check_out_date = check_out_date.split('T')[0]

            # Default language
            guest_language = booking_data.get('guest_language', 'en')

            # Validate required fields
            if not all([booking_id, guest_name, guest_email, hotel_name]):
                raise ValueError(f"Missing required booking information: booking_id={booking_id}, guest_name={guest_name}, guest_email={guest_email}, hotel_name={hotel_name}")

            # Check if booking already exists
            existing_booking = Booking.query.filter_by(booking_id=booking_id).first()
            if existing_booking:
                logger.info(f"Booking {booking_id} already exists, creating new chat session...")
                return self._update_existing_booking(existing_booking, booking_data)

            # Get coordinates for hotel location if available - try Google Maps link first
            coordinates = {'latitude': None, 'longitude': None}

            # Try to extract coordinates from Google Maps link first
            maps_link = booking_data.get('hotel_maps_link', '')
            if maps_link:
                coordinates = self._extract_coordinates_from_maps_link(maps_link)
                if coordinates and coordinates.get('latitude') and coordinates.get('longitude'):
                    logger.info(f"Successfully extracted coordinates from maps link: {coordinates}")
                else:
                    logger.warning(f"Failed to extract coordinates from maps link: {maps_link}")

            # Fallback to geocoding the address if maps link failed
            if not coordinates or not coordinates.get('latitude'):
                if hotel_location:
                    coordinates = self._get_coordinates(hotel_location)

            # Create new booking record
            booking = Booking(
                booking_id=booking_id,
                guest_name=guest_name,
                guest_email=guest_email,
                guest_phone=guest_phone,
                hotel_name=hotel_name,
                hotel_location=hotel_location or 'Location not provided',
                latitude=coordinates.get('latitude'),
                longitude=coordinates.get('longitude'),
                check_in_date=datetime.strptime(check_in_date, '%Y-%m-%d').date() if check_in_date else None,
                check_out_date=datetime.strptime(check_out_date, '%Y-%m-%d').date() if check_out_date else None,
                guest_language=guest_language,
                reference_number=reference_number,
                hotel_id=hotel_id,
                booking_status=booking_data.get('status', 'reserved'),
                booking_source=booking_data.get('source'),
                raw_event_data=booking_data  # Store raw data for debugging
            )
            
            db.session.add(booking)
            db.session.commit()
            
            # Create chat session and send welcome message
            chat_session = self.chatbot_service.create_chat_session(
                booking_id, 
                guest_language
            )
            
            logger.info(f"Successfully processed booking creation for {booking_id}")
            
            return {
                'status': 'success',
                'message': 'Booking processed and chat session created',
                'booking_id': booking_id,
                'session_id': chat_session['session_id'],
                'coordinates': coordinates
            }
            
        except Exception as e:
            logger.error(f"Error handling booking creation: {e}")
            db.session.rollback()
            raise
    
    def _handle_booking_updated(self, booking_data):
        """Handle booking update"""
        try:
            booking_id = booking_data.get('booking_id')
            
            if not booking_id:
                raise ValueError("Missing booking_id in update event")
            
            booking = Booking.query.filter_by(booking_id=booking_id).first()
            if not booking:
                logger.warning(f"Booking {booking_id} not found for update")
                return {'status': 'not_found', 'message': f'Booking {booking_id} not found'}
            
            # Update booking fields
            updated_fields = []
            
            if 'guest_name' in booking_data:
                booking.guest_name = booking_data['guest_name']
                updated_fields.append('guest_name')
            
            if 'guest_email' in booking_data:
                booking.guest_email = booking_data['guest_email']
                updated_fields.append('guest_email')
            
            if 'guest_phone' in booking_data:
                booking.guest_phone = booking_data['guest_phone']
                updated_fields.append('guest_phone')
            
            if 'hotel_location' in booking_data:
                booking.hotel_location = booking_data['hotel_location']

                # Try to extract coordinates from Google Maps link first, then address
                coordinates = {'latitude': None, 'longitude': None}
                maps_link = booking_data.get('hotel_maps_link', '')
                if maps_link:
                    coordinates = self._extract_coordinates_from_maps_link(maps_link)
                    if coordinates and coordinates.get('latitude') and coordinates.get('longitude'):
                        logger.info(f"Successfully extracted coordinates from maps link: {coordinates}")
                    else:
                        logger.warning(f"Failed to extract coordinates from maps link: {maps_link}")

                # Fallback to geocoding the address if maps link failed
                if not coordinates or not coordinates.get('latitude'):
                    coordinates = self._get_coordinates(booking_data['hotel_location'])

                booking.latitude = coordinates.get('latitude')
                booking.longitude = coordinates.get('longitude')
                updated_fields.extend(['hotel_location', 'coordinates'])
            
            if 'check_in_date' in booking_data:
                booking.check_in_date = datetime.strptime(
                    booking_data['check_in_date'], '%Y-%m-%d'
                ).date()
                updated_fields.append('check_in_date')
            
            if 'check_out_date' in booking_data:
                booking.check_out_date = datetime.strptime(
                    booking_data['check_out_date'], '%Y-%m-%d'
                ).date()
                updated_fields.append('check_out_date')
            
            if 'guest_language' in booking_data:
                booking.guest_language = booking_data['guest_language']
                updated_fields.append('guest_language')
            
            db.session.commit()
            
            logger.info(f"Updated booking {booking_id}, fields: {updated_fields}")
            
            return {
                'status': 'success',
                'message': 'Booking updated successfully',
                'booking_id': booking_id,
                'updated_fields': updated_fields
            }
            
        except Exception as e:
            logger.error(f"Error handling booking update: {e}")
            db.session.rollback()
            raise
    
    def _handle_booking_cancelled(self, booking_data):
        """Handle booking cancellation"""
        try:
            booking_id = booking_data.get('booking_id')
            
            if not booking_id:
                raise ValueError("Missing booking_id in cancellation event")
            
            booking = Booking.query.filter_by(booking_id=booking_id).first()
            if not booking:
                logger.warning(f"Booking {booking_id} not found for cancellation")
                return {'status': 'not_found', 'message': f'Booking {booking_id} not found'}
            
            # Deactivate associated chat sessions
            for chat_session in booking.chat_sessions:
                chat_session.is_active = False
            
            # Note: We don't delete the booking record for audit purposes
            # You might want to add a 'status' field to mark it as cancelled
            
            db.session.commit()
            
            logger.info(f"Processed cancellation for booking {booking_id}")
            
            return {
                'status': 'success',
                'message': 'Booking cancellation processed',
                'booking_id': booking_id
            }
            
        except Exception as e:
            logger.error(f"Error handling booking cancellation: {e}")
            db.session.rollback()
            raise
    
    def _update_existing_booking(self, booking, booking_data):
        """Update existing booking with new data and create a new chat session"""
        try:
            # Update fields if provided
            if 'guest_name' in booking_data:
                booking.guest_name = booking_data['guest_name']

            if 'guest_email' in booking_data:
                booking.guest_email = booking_data['guest_email']

            if 'hotel_location' in booking_data:
                booking.hotel_location = booking_data['hotel_location']

                # Try to extract coordinates from Google Maps link first, then address
                coordinates = {'latitude': None, 'longitude': None}
                maps_link = booking_data.get('hotel_maps_link', '')
                if maps_link:
                    coordinates = self._extract_coordinates_from_maps_link(maps_link)
                    if coordinates and coordinates.get('latitude') and coordinates.get('longitude'):
                        logger.info(f"Successfully extracted coordinates from maps link: {coordinates}")
                    else:
                        logger.warning(f"Failed to extract coordinates from maps link: {maps_link}")

                # Fallback to geocoding the address if maps link failed
                if not coordinates or not coordinates.get('latitude'):
                    coordinates = self._get_coordinates(booking_data['hotel_location'])

                booking.latitude = coordinates.get('latitude')
                booking.longitude = coordinates.get('longitude')

            # Always create a new chat session for existing bookings too
            from chatbot.models import ChatSession, ChatMessage
            import uuid

            # Create new chat session
            session = ChatSession(
                session_id=str(uuid.uuid4()),
                booking_id=booking.id,
                guest_language=booking.guest_language,
                is_active=True
            )

            db.session.add(session)
            db.session.commit()

            logger.info(f"Created new chat session {session.session_id} for existing booking {booking.booking_id}")

            # Send welcome message (replicate the logic from create_chat_session)
            welcome_message = self.translation_service.get_welcome_message(
                booking.guest_name,
                booking.hotel_name,
                booking.guest_language
            )

            # Add welcome message
            welcome_msg = ChatMessage(
                session_id=session.id,
                message_type='bot',
                content=welcome_message,
                message_metadata={'type': 'welcome', 'booking_id': booking.booking_id}
            )
            db.session.add(welcome_msg)

            # Send category options
            category_options = self.translation_service.get_category_options(booking.guest_language)
            options_message = self._format_category_options(category_options, booking.guest_language)

            options_msg = ChatMessage(
                session_id=session.id,
                message_type='bot',
                content=options_message,
                message_metadata={'type': 'category_options', 'options': category_options}
            )
            db.session.add(options_msg)

            db.session.commit()

            return {
                'status': 'success',
                'message': 'Booking updated and new chat session created',
                'booking_id': booking.booking_id,
                'session_id': session.session_id,
                'coordinates': {
                    'latitude': booking.latitude,
                    'longitude': booking.longitude
                }
            }

        except Exception as e:
            logger.error(f"Error updating existing booking: {e}")
            db.session.rollback()
            raise

    def _format_category_options(self, options, language):
        """Format category options message"""
        headers = {
            'en': "What would you like to explore? Choose from:",
            'hi': "आप क्या खोजना चाहेंगे? इनमें से चुनें:",
            'es': "¿Qué te gustaría explorar? Elige entre:",
            'fr': "Que souhaitez-vous explorer? Choisissez parmi:"
        }

        message = headers.get(language, headers['en']) + "\n\n"

        for key, value in options.items():
            message += f"• {value}\n"

        return message
    
    def _get_coordinates(self, location_string):
        """Get latitude and longitude for a location using Nominatim geocoding"""
        try:
            logger.info(f"Geocoding location: {location_string}")

            # Try different variations of the address for better geocoding success
            address_variations = [
                location_string,  # Original address
                # Extract city and state from the address
                self._extract_city_state(location_string),
                # Try just the city name
                self._extract_city_name(location_string)
            ]

            for address in address_variations:
                if address:
                    logger.info(f"Trying geocoding with: {address}")
                    location = self.geocoder.geocode(address)
                    if location:
                        logger.info(f"Successfully geocoded '{address}' to: {location.latitude}, {location.longitude}")
                        return {
                            'latitude': location.latitude,
                            'longitude': location.longitude
                        }

            logger.warning(f"Could not geocode location with any variation: {location_string}")
            return {'latitude': None, 'longitude': None}

        except Exception as e:
            logger.error(f"Error geocoding location {location_string}: {e}")
            return {'latitude': None, 'longitude': None}

    def _extract_city_state(self, address):
        """Extract city and state from address for better geocoding"""
        try:
            # Look for common patterns in Indian addresses
            if 'Bengaluru' in address or 'Bangalore' in address:
                return 'Bengaluru, Karnataka, India'
            elif 'Mumbai' in address:
                return 'Mumbai, Maharashtra, India'
            elif 'Delhi' in address:
                return 'Delhi, India'
            elif 'Chennai' in address:
                return 'Chennai, Tamil Nadu, India'
            elif 'Kolkata' in address:
                return 'Kolkata, West Bengal, India'
            elif 'Hyderabad' in address:
                return 'Hyderabad, Telangana, India'
            elif 'Pune' in address:
                return 'Pune, Maharashtra, India'

            # Try to extract state and city from the address
            parts = address.split(',')
            if len(parts) >= 2:
                # Look for state names in the address
                for part in reversed(parts):
                    part = part.strip()
                    if any(state in part for state in ['Karnataka', 'Maharashtra', 'Delhi', 'Tamil Nadu', 'West Bengal', 'Telangana']):
                        # Find the city part (usually before the state)
                        state_index = parts.index(next(p for p in parts if state in p))
                        if state_index > 0:
                            city = parts[state_index - 1].strip()
                            return f"{city}, {part}, India"
                        else:
                            return f"{part}, India"

            return None
        except Exception as e:
            logger.error(f"Error extracting city/state from address: {e}")
            return None

    def _extract_city_name(self, address):
        """Extract just the city name from address"""
        try:
            # Common city name patterns
            city_patterns = [
                'Bengaluru', 'Bangalore', 'Mumbai', 'Delhi', 'New Delhi',
                'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad',
                'Jaipur', 'Surat', 'Lucknow', 'Kanpur', 'Nagpur'
            ]

            for city in city_patterns:
                if city in address:
                    return f"{city}, India"

            # If no known city found, try to extract from comma-separated parts
            parts = address.split(',')
            for part in parts:
                part = part.strip()
                # Look for parts that might be city names (avoid street addresses)
                if len(part) > 3 and not any(char.isdigit() for char in part[:3]):
                    return f"{part}, India"

            return None
        except Exception as e:
            logger.error(f"Error extracting city name from address: {e}")
            return None

    def _extract_coordinates_from_maps_link(self, maps_link):
        """Extract latitude and longitude from Google Maps link"""
        try:
            import re

            logger.info(f"Extracting coordinates from maps link: {maps_link}")

            # Google Maps URLs can have coordinates in different formats:
            # Format 1: /@latitude,longitude,zoom
            # Format 2: /place/name/@latitude,longitude,zoom
            # Format 3: ?q=latitude,longitude
            # Format 4: 3d parameter for latitude and 4d parameter for longitude

            # Try format 1 and 2: /@latitude,longitude
            pattern1 = r'/@(-?\d+\.?\d*),(-?\d+\.?\d*)'
            match = re.search(pattern1, maps_link)
            if match:
                latitude = float(match.group(1))
                longitude = float(match.group(2))
                logger.info(f"Extracted coordinates using pattern 1: {latitude}, {longitude}")
                return {'latitude': latitude, 'longitude': longitude}

            # Try format 3: ?q=latitude,longitude
            pattern2 = r'\?q=(-?\d+\.?\d*),(-?\d+\.?\d*)'
            match = re.search(pattern2, maps_link)
            if match:
                latitude = float(match.group(1))
                longitude = float(match.group(2))
                logger.info(f"Extracted coordinates using pattern 2: {latitude}, {longitude}")
                return {'latitude': latitude, 'longitude': longitude}

            # Try format 4: 3d and 4d parameters
            lat_pattern = r'3d(-?\d+\.?\d*)'
            lng_pattern = r'4d(-?\d+\.?\d*)'

            lat_match = re.search(lat_pattern, maps_link)
            lng_match = re.search(lng_pattern, maps_link)

            if lat_match and lng_match:
                latitude = float(lat_match.group(1))
                longitude = float(lng_match.group(1))
                logger.info(f"Extracted coordinates using pattern 3: {latitude}, {longitude}")
                return {'latitude': latitude, 'longitude': longitude}

            # Try to find any coordinate-like patterns in the URL
            coord_pattern = r'(-?\d+\.?\d+),(-?\d+\.?\d+)'
            matches = re.findall(coord_pattern, maps_link)

            for match in matches:
                try:
                    lat, lng = float(match[0]), float(match[1])
                    # Basic validation: latitude should be between -90 and 90, longitude between -180 and 180
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        logger.info(f"Extracted coordinates using general pattern: {lat}, {lng}")
                        return {'latitude': lat, 'longitude': lng}
                except ValueError:
                    continue

            logger.warning(f"Could not extract coordinates from maps link: {maps_link}")
            return {'latitude': None, 'longitude': None}

        except Exception as e:
            logger.error(f"Error extracting coordinates from maps link: {e}")
            return {'latitude': None, 'longitude': None}
    
    def get_booking_summary(self, booking_id):
        """Get booking summary for debugging/monitoring"""
        try:
            booking = Booking.query.filter_by(booking_id=booking_id).first()
            if not booking:
                return None

            return {
                'booking': booking.to_dict(),
                'chat_sessions': len(booking.chat_sessions),
                'active_sessions': len([s for s in booking.chat_sessions if s.is_active])
            }

        except Exception as e:
            logger.error(f"Error getting booking summary: {e}")
            return None

    def process_api_booking_data(self, bookings_data: List[Dict]) -> Dict:
        """
        Process booking data from external API response and create bookings/chat sessions

        Args:
            bookings_data (List[Dict]): List of booking data from API

        Returns:
            Dict: Processing result with created bookings and sessions
        """
        try:
            results = {
                'status': 'success',
                'processed_bookings': [],
                'created_sessions': [],
                'errors': []
            }

            for booking_data in bookings_data:
                try:
                    # Process each booking
                    result = self._process_single_api_booking(booking_data)

                    if result['status'] == 'success':
                        results['processed_bookings'].append(result['booking_id'])
                        if 'session_id' in result:
                            results['created_sessions'].append(result['session_id'])
                    else:
                        results['errors'].append({
                            'booking_data': booking_data,
                            'error': result.get('message', 'Unknown error')
                        })

                except Exception as e:
                    logger.error(f"Error processing individual booking: {e}")
                    results['errors'].append({
                        'booking_data': booking_data,
                        'error': str(e)
                    })

            logger.info(f"Processed {len(results['processed_bookings'])} bookings, "
                       f"created {len(results['created_sessions'])} sessions, "
                       f"{len(results['errors'])} errors")

            return results

        except Exception as e:
            logger.error(f"Error processing API booking data: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'processed_bookings': [],
                'created_sessions': [],
                'errors': []
            }

    def _process_single_api_booking(self, booking_data: Dict) -> Dict:
        """
        Process a single booking from API data

        Args:
            booking_data (Dict): Single booking data from API

        Returns:
            Dict: Processing result
        """
        try:
            # Extract required fields
            booking_id = booking_data.get('booking_id')
            guest_name = booking_data.get('guest_name', 'Guest')
            guest_email = booking_data.get('guest_email', '')
            guest_phone = booking_data.get('guest_phone', '')
            hotel_name = booking_data.get('hotel_name', 'Hotel')
            hotel_location = booking_data.get('hotel_location', 'Location not provided')

            # Validate required fields
            if not booking_id:
                raise ValueError("Missing booking_id in API data")

            if not guest_email:
                logger.warning(f"No guest email for booking {booking_id}")
                guest_email = f"guest_{booking_id}@example.com"  # Fallback email

            # Check if booking already exists
            existing_booking = Booking.query.filter_by(booking_id=booking_id).first()
            if existing_booking:
                logger.info(f"Booking {booking_id} already exists, creating new chat session...")
                return self._update_existing_booking(existing_booking, booking_data)

            # Get coordinates for hotel location - try Google Maps link first, then address
            coordinates = {'latitude': None, 'longitude': None}

            # Try to extract coordinates from Google Maps link first
            maps_link = booking_data.get('hotel_maps_link', '')
            if maps_link:
                coordinates = self._extract_coordinates_from_maps_link(maps_link)
                if coordinates and coordinates.get('latitude') and coordinates.get('longitude'):
                    logger.info(f"Successfully extracted coordinates from maps link: {coordinates}")
                else:
                    logger.warning(f"Failed to extract coordinates from maps link: {maps_link}")

            # Fallback to geocoding the address if maps link failed
            if not coordinates or not coordinates.get('latitude'):
                if hotel_location and hotel_location != 'Location not provided':
                    coordinates = self._get_coordinates(hotel_location)

            # Parse dates
            check_in_date = None
            check_out_date = None

            if booking_data.get('check_in_date'):
                try:
                    check_in_date = datetime.strptime(booking_data['check_in_date'], '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Could not parse check_in_date: {booking_data['check_in_date']}")

            if booking_data.get('check_out_date'):
                try:
                    check_out_date = datetime.strptime(booking_data['check_out_date'], '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Could not parse check_out_date: {booking_data['check_out_date']}")

            # Create new booking record
            booking = Booking(
                booking_id=booking_id,
                guest_name=guest_name,
                guest_email=guest_email,
                guest_phone=guest_phone,
                hotel_name=hotel_name,
                hotel_location=hotel_location,
                latitude=coordinates.get('latitude'),
                longitude=coordinates.get('longitude'),
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                guest_language=booking_data.get('guest_language', 'en'),
                reference_number=booking_data.get('reference_number'),
                hotel_id=booking_data.get('hotel_id'),
                booking_status=booking_data.get('booking_status', 'confirmed'),
                booking_source=booking_data.get('booking_source'),
                raw_event_data=booking_data  # Store raw data for debugging
            )

            db.session.add(booking)
            db.session.commit()

            # Create chat session and send welcome message
            chat_session = self.chatbot_service.create_chat_session(
                booking_id,
                booking_data.get('guest_language', 'en')
            )

            logger.info(f"Successfully processed API booking for {booking_id}")

            return {
                'status': 'success',
                'message': 'Booking processed and chat session created',
                'booking_id': booking_id,
                'session_id': chat_session['session_id'],
                'coordinates': coordinates
            }

        except Exception as e:
            logger.error(f"Error processing single API booking: {e}")
            db.session.rollback()
            return {
                'status': 'error',
                'message': str(e),
                'booking_data': booking_data
            }
