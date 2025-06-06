from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
from datetime import datetime, timedelta
from config.config import config
from config.database import init_db, db
from chatbot.event_handler import EventHandler
from chatbot.chatbot_service import ChatbotService
from chatbot.user_service import UserService
from chatbot.booking_search_service import BookingSearchService
from chatbot.models import Booking, ChatSession, ChatMessage, User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """Create Flask application"""
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])

    # Enable CORS
    CORS(app)

    # Initialize database
    init_db(app)

    # Initialize services
    event_handler = EventHandler()
    chatbot_service = ChatbotService()
    user_service = UserService()
    booking_search_service = BookingSearchService()

    @app.route('/')
    def index():
        """Serve the TravelMate chatbot interface"""
        return send_from_directory('static', 'index.html')

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'treebo-chatbot'
        })

    @app.route('/webhook/booking', methods=['POST'])
    def booking_webhook():
        """Webhook endpoint for receiving booking events"""
        try:
            # Verify webhook signature if configured
            signature = request.headers.get('X-Signature-256')
            if signature and app.config.get('WEBHOOK_SECRET'):
                if not event_handler.verify_webhook_signature(
                    request.data,
                    signature,
                    app.config['WEBHOOK_SECRET']
                ):
                    logger.warning("Invalid webhook signature")
                    return jsonify({'error': 'Invalid signature'}), 401

            # Process the event
            event_data = request.get_json()
            if not event_data:
                return jsonify({'error': 'No JSON data provided'}), 400

            logger.info(f"Received booking event: {event_data.get('event_type')}")

            result = event_handler.process_booking_event(event_data)

            return jsonify(result), 200

        except ValueError as e:
            logger.error(f"Validation error in booking webhook: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error in booking webhook: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/chat/session', methods=['POST'])
    def create_chat_session():
        """Create a new chat session"""
        try:
            data = request.get_json()
            booking_id = data.get('booking_id')
            guest_language = data.get('language', 'en')

            if not booking_id:
                return jsonify({'error': 'booking_id is required'}), 400

            result = chatbot_service.create_chat_session(booking_id, guest_language)

            return jsonify(result), 200

        except ValueError as e:
            logger.error(f"Validation error creating chat session: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/chat/message', methods=['POST'])
    def send_message():
        """Send a message to the chatbot"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            message = data.get('message')
            message_type = data.get('type', 'text')

            if not session_id or not message:
                return jsonify({'error': 'session_id and message are required'}), 400

            result = chatbot_service.process_user_message(session_id, message, message_type)

            return jsonify(result), 200

        except ValueError as e:
            logger.error(f"Validation error processing message: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/chat/recommendations/<session_id>/<category>', methods=['GET'])
    def get_recommendations(session_id, category):
        """Get recommendations for a specific category"""
        try:
            valid_categories = ['restaurants', 'sightseeing', 'shopping', 'nightlife', 'atms', 'pharmacy', 'rentals']
            if category not in valid_categories:
                return jsonify({'error': f'Invalid category. Must be one of: {valid_categories}'}), 400

            result = chatbot_service.get_recommendations(session_id, category)

            return jsonify(result), 200

        except ValueError as e:
            logger.error(f"Validation error getting recommendations: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/chat/history/<session_id>', methods=['GET'])
    def get_chat_history(session_id):
        """Get chat history for a session"""
        try:
            result = chatbot_service.get_chat_history(session_id)

            return jsonify(result), 200

        except ValueError as e:
            logger.error(f"Validation error getting chat history: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/chat/itinerary/<session_id>', methods=['GET'])
    def get_itinerary(session_id):
        """Generate AI-powered itinerary for a session"""
        try:
            result = chatbot_service.get_itinerary(session_id)

            return jsonify(result), 200

        except ValueError as e:
            logger.error(f"Validation error getting itinerary: {e}")
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error getting itinerary: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/booking/<booking_id>', methods=['GET'])
    def get_booking(booking_id):
        """Get booking information"""
        try:
            booking = Booking.query.filter_by(booking_id=booking_id).first()
            if not booking:
                return jsonify({'error': 'Booking not found'}), 404

            return jsonify(booking.to_dict()), 200

        except Exception as e:
            logger.error(f"Error getting booking: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/booking/<booking_id>/sessions', methods=['GET'])
    def get_booking_sessions(booking_id):
        """Get all chat sessions for a booking"""
        try:
            booking = Booking.query.filter_by(booking_id=booking_id).first()
            if not booking:
                return jsonify({'error': 'Booking not found'}), 404

            sessions = []
            for session in booking.chat_sessions:
                sessions.append({
                    'session_id': session.session_id,
                    'language': session.guest_language,
                    'is_active': session.is_active,
                    'created_at': session.created_at.isoformat(),
                    'updated_at': session.updated_at.isoformat(),
                    'message_count': len(session.messages)
                })

            return jsonify({
                'booking_id': booking_id,
                'sessions': sessions
            }), 200

        except Exception as e:
            logger.error(f"Error getting booking sessions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/user/login', methods=['POST'])
    def user_login():
        """User login/registration endpoint"""
        try:
            data = request.get_json()
            phone_number = data.get('phone_number')
            name = data.get('name')
            email = data.get('email')

            if not phone_number:
                return jsonify({'error': 'phone_number is required'}), 400

            result = user_service.create_or_get_user(phone_number, name, email)

            if result['status'] == 'success':
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error in user login: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/user/validate', methods=['POST'])
    def validate_user_session():
        """Validate user session token"""
        try:
            data = request.get_json()
            session_token = data.get('session_token')

            if not session_token:
                return jsonify({'error': 'session_token is required'}), 400

            result = user_service.validate_session(session_token)

            if result['status'] == 'valid':
                return jsonify(result), 200
            else:
                return jsonify(result), 401

        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/user/logout', methods=['POST'])
    def user_logout():
        """User logout endpoint"""
        try:
            data = request.get_json()
            session_token = data.get('session_token')

            if not session_token:
                return jsonify({'error': 'session_token is required'}), 400

            result = user_service.logout_user(session_token)

            return jsonify(result), 200

        except Exception as e:
            logger.error(f"Error in user logout: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/bookings/search', methods=['POST'])
    def search_user_bookings():
        """Search bookings for logged-in user using external API"""
        try:
            data = request.get_json()
            session_token = data.get('session_token')
            from_date = data.get('from_date')  # Optional, defaults to current date

            if not session_token:
                return jsonify({'error': 'session_token is required'}), 400

            # Validate user session
            user_validation = user_service.validate_session(session_token)
            if user_validation['status'] != 'valid':
                return jsonify({'error': 'Invalid session token'}), 401

            phone_number = user_validation['phone_number']

            # Search bookings using external API
            api_result = booking_search_service.search_bookings_by_phone(phone_number, from_date)

            if api_result['status'] != 'success':
                return jsonify(api_result), 400

            # Process the API response to extract booking data
            bookings_data = booking_search_service.process_booking_response(api_result)

            if not bookings_data:
                return jsonify({
                    'status': 'success',
                    'message': 'No bookings found',
                    'bookings': [],
                    'sessions': []
                }), 200

            # Process bookings and create chat sessions
            processing_result = event_handler.process_api_booking_data(bookings_data)

            return jsonify({
                'status': 'success',
                'message': f'Found and processed {len(processing_result["processed_bookings"])} bookings',
                'api_result': api_result,
                'bookings': processing_result['processed_bookings'],
                'sessions': processing_result['created_sessions'],
                'errors': processing_result['errors']
            }), 200

        except Exception as e:
            logger.error(f"Error searching user bookings: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/admin/stats', methods=['GET'])
    def get_stats():
        """Get system statistics"""
        try:
            total_bookings = Booking.query.count()
            total_sessions = ChatSession.query.count()
            active_sessions = ChatSession.query.filter_by(is_active=True).count()
            total_messages = ChatMessage.query.count()

            # Calculate average response time (mock data for now)
            avg_response_time = 250

            # Count recommendations given
            recommendations_count = ChatMessage.query.filter(
                ChatMessage.content.contains('recommendations')
            ).count()

            # Calculate error rate (mock data for now)
            error_rate = 2.5

            return jsonify({
                'total_bookings': total_bookings,
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'total_messages': total_messages,
                'avg_response_time': avg_response_time,
                'recommendations_count': recommendations_count,
                'error_rate': error_rate,
                'timestamp': datetime.utcnow().isoformat()
            }), 200

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/admin/sessions', methods=['GET'])
    def get_admin_sessions():
        """Get all chat sessions for admin dashboard"""
        try:
            sessions = ChatSession.query.order_by(ChatSession.created_at.desc()).limit(20).all()

            sessions_data = []
            for session in sessions:
                sessions_data.append({
                    'session_id': session.session_id,
                    'guest_name': session.guest_name,
                    'hotel_location': session.hotel_location,
                    'created_at': session.created_at.isoformat(),
                    'is_active': session.is_active
                })

            return jsonify(sessions_data), 200

        except Exception as e:
            logger.error(f"Error getting admin sessions: {str(e)}")
            return jsonify({'error': 'Failed to get sessions'}), 500

    @app.route('/admin/messages', methods=['GET'])
    def get_admin_messages():
        """Get recent messages for admin dashboard"""
        try:
            messages = ChatMessage.query.order_by(
                ChatMessage.timestamp.desc()
            ).limit(50).all()

            messages_data = []
            for message in messages:
                messages_data.append({
                    'session_id': message.session_id,
                    'message_type': message.message_type,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat()
                })

            return jsonify(messages_data), 200

        except Exception as e:
            logger.error(f"Error getting admin messages: {str(e)}")
            return jsonify({'error': 'Failed to get messages'}), 500

    @app.route('/admin/clear-sessions', methods=['POST'])
    def clear_old_sessions():
        """Clear old inactive sessions"""
        try:
            # Delete sessions older than 24 hours and inactive
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            old_sessions = ChatSession.query.filter(
                ChatSession.created_at < cutoff_time,
                ChatSession.is_active == False
            ).all()

            count = len(old_sessions)
            for session in old_sessions:
                db.session.delete(session)

            db.session.commit()

            return jsonify({
                'message': f'Cleared {count} old sessions',
                'count': count
            }), 200

        except Exception as e:
            logger.error(f"Error clearing sessions: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to clear sessions'}), 500

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'

    logger.info(f"Starting Treebo Chatbot service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
