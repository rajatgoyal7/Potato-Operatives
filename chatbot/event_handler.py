import logging
import json
from datetime import datetime
from chatbot.models import Booking, db
from chatbot.chatbot_service import ChatbotService
from chatbot.translation_service import TranslationService
from geopy.geocoders import Nominatim
import hashlib
import hmac

logger = logging.getLogger(__name__)

class EventHandler:
    """Handler for processing booking events"""
    
    def __init__(self):
        self.chatbot_service = ChatbotService()
        self.translation_service = TranslationService()
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
            # Extract booking information
            booking_id = booking_data.get('booking_id')
            guest_name = booking_data.get('guest_name')
            guest_email = booking_data.get('guest_email')
            guest_phone = booking_data.get('guest_phone')
            hotel_name = booking_data.get('hotel_name')
            hotel_location = booking_data.get('hotel_location')
            check_in_date = booking_data.get('check_in_date')
            check_out_date = booking_data.get('check_out_date')
            guest_language = booking_data.get('guest_language', 'en')
            
            # Validate required fields
            if not all([booking_id, guest_name, guest_email, hotel_name, hotel_location]):
                raise ValueError("Missing required booking information")
            
            # Check if booking already exists
            existing_booking = Booking.query.filter_by(booking_id=booking_id).first()
            if existing_booking:
                logger.info(f"Booking {booking_id} already exists, updating...")
                return self._update_existing_booking(existing_booking, booking_data)
            
            # Get coordinates for hotel location
            coordinates = self._get_coordinates(hotel_location)
            
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
                check_in_date=datetime.strptime(check_in_date, '%Y-%m-%d').date() if check_in_date else None,
                check_out_date=datetime.strptime(check_out_date, '%Y-%m-%d').date() if check_out_date else None,
                guest_language=guest_language
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
        """Update existing booking with new data"""
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
            
            db.session.commit()
            
            return {
                'status': 'updated',
                'message': 'Existing booking updated',
                'booking_id': booking.booking_id
            }
            
        except Exception as e:
            logger.error(f"Error updating existing booking: {e}")
            db.session.rollback()
            raise
    
    def _get_coordinates(self, location_string):
        """Get latitude and longitude for a location"""
        try:
            location = self.geocoder.geocode(location_string)
            if location:
                return {
                    'latitude': location.latitude,
                    'longitude': location.longitude
                }
            else:
                logger.warning(f"Could not geocode location: {location_string}")
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
