import logging
import json
from datetime import datetime
from chatbot.models import Booking, db
from chatbot.chatbot_service import ChatbotService
from chatbot.translation_service import TranslationService
from chatbot.mapmyindia_service import MapMyIndiaService
from geopy.geocoders import Nominatim
import hashlib
import hmac

logger = logging.getLogger(__name__)

class EventHandler:
    """Handler for processing booking events"""

    def __init__(self):
        self.chatbot_service = ChatbotService()
        self.translation_service = TranslationService()
        self.mapmyindia_service = MapMyIndiaService()
        # Keep Nominatim as fallback
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

            # Get coordinates for hotel location if available
            coordinates = {'latitude': None, 'longitude': None}
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
        """Get latitude and longitude for a location using MapMyIndia API"""
        try:
            # Try MapMyIndia first
            result = self.mapmyindia_service.geocode_location(location_string)
            if result and result.get('latitude') and result.get('longitude'):
                return {
                    'latitude': result['latitude'],
                    'longitude': result['longitude']
                }

            # Fallback to Nominatim
            logger.info(f"MapMyIndia geocoding failed, trying Nominatim for: {location_string}")
            location = self.geocoder.geocode(location_string)
            if location:
                return {
                    'latitude': location.latitude,
                    'longitude': location.longitude
                }
            else:
                logger.warning(f"Could not geocode location with any service: {location_string}")
                return {'latitude': None, 'longitude': None}

        except Exception as e:
            logger.error(f"Error geocoding location {location_string}: {e}")
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
