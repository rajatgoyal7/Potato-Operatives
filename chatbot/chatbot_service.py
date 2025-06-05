import logging
import uuid
from datetime import datetime
from chatbot.models import ChatSession, ChatMessage, Booking, db
from chatbot.recommendation_engine import RecommendationEngine
from chatbot.translation_service import TranslationService
from config.database import get_redis_client
import json

logger = logging.getLogger(__name__)

class ChatbotService:
    """Main chatbot service for handling user interactions"""

    def __init__(self):
        self.recommendation_engine = RecommendationEngine()
        self.translation_service = TranslationService()
        self.redis_client = get_redis_client()

    def create_chat_session(self, booking_id, guest_language='en'):
        """Create a new chat session for a booking"""
        try:
            booking = Booking.query.filter_by(booking_id=booking_id).first()
            if not booking:
                raise ValueError(f"Booking {booking_id} not found")

            session_id = str(uuid.uuid4())

            chat_session = ChatSession(
                session_id=session_id,
                booking_id=booking.id,
                guest_language=guest_language or booking.guest_language
            )

            db.session.add(chat_session)
            db.session.commit()

            # Send welcome message
            welcome_message = self.translation_service.get_welcome_message(
                booking.guest_name,
                booking.hotel_name,
                guest_language
            )

            self._add_message(
                chat_session.id,
                'bot',
                welcome_message,
                {'type': 'welcome', 'booking_id': booking_id}
            )

            # Send category options
            category_options = self.translation_service.get_category_options(guest_language)
            options_message = self._format_category_options(category_options, guest_language)

            self._add_message(
                chat_session.id,
                'bot',
                options_message,
                {'type': 'category_options', 'options': category_options}
            )

            return {
                'session_id': session_id,
                'booking': booking.to_dict(),
                'messages': self._get_session_messages(chat_session.id)
            }

        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            raise

    def process_user_message(self, session_id, message, message_type='text'):
        """Process user message and generate response"""
        try:
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            booking = chat_session.booking

            # Add user message
            self._add_message(chat_session.id, 'user', message)

            # Detect intent and generate response
            response = self._generate_response(message, booking, chat_session.guest_language)

            # Add bot response
            self._add_message(
                chat_session.id,
                'bot',
                response['message'],
                response.get('metadata', {})
            )

            # Update session timestamp
            chat_session.updated_at = datetime.utcnow()
            db.session.commit()

            return {
                'session_id': session_id,
                'response': response,
                'messages': self._get_session_messages(chat_session.id)
            }

        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            raise

    def get_recommendations(self, session_id, category):
        """Get recommendations for a specific category"""
        try:
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            booking = chat_session.booking

            # Get recommendations
            recommendations = self.recommendation_engine.get_recommendations(
                booking.latitude,
                booking.longitude,
                category,
                chat_session.guest_language
            )

            # Translate recommendations if needed
            if chat_session.guest_language != 'en':
                recommendations = self.translation_service.translate_recommendations(
                    recommendations,
                    chat_session.guest_language
                )

            # Format response message
            response_message = self._format_recommendations_message(
                recommendations,
                category,
                chat_session.guest_language
            )

            # Add bot message with recommendations
            self._add_message(
                chat_session.id,
                'bot',
                response_message,
                {
                    'type': 'recommendations',
                    'category': category,
                    'recommendations': recommendations
                }
            )

            return {
                'session_id': session_id,
                'category': category,
                'recommendations': recommendations,
                'message': response_message
            }

        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            raise

    def _generate_response(self, user_message, booking, language):
        """Generate appropriate response based on user message"""
        user_message_lower = user_message.lower()

        # Simple intent detection (can be enhanced with NLP)
        if any(word in user_message_lower for word in ['restaurant', 'food', 'eat', 'dining']):
            return self._handle_restaurant_request(booking, language)
        elif any(word in user_message_lower for word in ['sightseeing', 'attraction', 'visit', 'see']):
            return self._handle_sightseeing_request(booking, language)
        elif any(word in user_message_lower for word in ['event', 'show', 'concert', 'festival']):
            return self._handle_event_request(booking, language)
        elif any(word in user_message_lower for word in ['shop', 'shopping', 'buy', 'mall']):
            return self._handle_shopping_request(booking, language)
        elif any(word in user_message_lower for word in ['nightlife', 'bar', 'club', 'night']):
            return self._handle_nightlife_request(booking, language)
        else:
            return self._handle_general_request(user_message, language)

    def _handle_restaurant_request(self, booking, language):
        """Handle restaurant recommendation request"""
        recommendations = self.recommendation_engine.get_recommendations(
            booking.latitude,
            booking.longitude,
            'restaurants',
            language
        )

        if language != 'en':
            recommendations = self.translation_service.translate_recommendations(
                recommendations, language
            )

        message = self._format_recommendations_message(recommendations, 'restaurants', language)

        return {
            'message': message,
            'metadata': {
                'type': 'recommendations',
                'category': 'restaurants',
                'recommendations': recommendations
            }
        }

    def _handle_sightseeing_request(self, booking, language):
        """Handle sightseeing recommendation request"""
        recommendations = self.recommendation_engine.get_recommendations(
            booking.latitude,
            booking.longitude,
            'sightseeing',
            language
        )

        if language != 'en':
            recommendations = self.translation_service.translate_recommendations(
                recommendations, language
            )

        message = self._format_recommendations_message(recommendations, 'sightseeing', language)

        return {
            'message': message,
            'metadata': {
                'type': 'recommendations',
                'category': 'sightseeing',
                'recommendations': recommendations
            }
        }

    def _handle_event_request(self, booking, language):
        """Handle event recommendation request"""
        recommendations = self.recommendation_engine.get_recommendations(
            booking.latitude,
            booking.longitude,
            'events',
            language
        )

        message = self._format_recommendations_message(recommendations, 'events', language)

        return {
            'message': message,
            'metadata': {
                'type': 'recommendations',
                'category': 'events',
                'recommendations': recommendations
            }
        }

    def _handle_shopping_request(self, booking, language):
        """Handle shopping recommendation request"""
        recommendations = self.recommendation_engine.get_recommendations(
            booking.latitude,
            booking.longitude,
            'shopping',
            language
        )

        if language != 'en':
            recommendations = self.translation_service.translate_recommendations(
                recommendations, language
            )

        message = self._format_recommendations_message(recommendations, 'shopping', language)

        return {
            'message': message,
            'metadata': {
                'type': 'recommendations',
                'category': 'shopping',
                'recommendations': recommendations
            }
        }

    def _handle_nightlife_request(self, booking, language):
        """Handle nightlife recommendation request"""
        recommendations = self.recommendation_engine.get_recommendations(
            booking.latitude,
            booking.longitude,
            'nightlife',
            language
        )

        if language != 'en':
            recommendations = self.translation_service.translate_recommendations(
                recommendations, language
            )

        message = self._format_recommendations_message(recommendations, 'nightlife', language)

        return {
            'message': message,
            'metadata': {
                'type': 'recommendations',
                'category': 'nightlife',
                'recommendations': recommendations
            }
        }

    def _handle_general_request(self, user_message, language):
        """Handle general requests"""
        responses = {
            'en': "I can help you discover amazing places around your hotel! You can ask me about restaurants, sightseeing attractions, events, shopping, or nightlife. What interests you most?",
            'hi': "मैं आपके होटल के आसपास के अद्भुत स्थानों की खोज में आपकी मदद कर सकता हूं! आप मुझसे रेस्तरां, दर्शनीय स्थल, कार्यक्रम, खरीदारी या रात्रि जीवन के बारे में पूछ सकते हैं। आपको सबसे ज्यादा क्या दिलचस्पी है?",
            'es': "¡Puedo ayudarte a descubrir lugares increíbles alrededor de tu hotel! Puedes preguntarme sobre restaurantes, atracciones turísticas, eventos, compras o vida nocturna. ¿Qué te interesa más?",
            'fr': "Je peux vous aider à découvrir des endroits incroyables autour de votre hôtel! Vous pouvez me demander des restaurants, des attractions touristiques, des événements, du shopping ou de la vie nocturne. Qu'est-ce qui vous intéresse le plus?"
        }

        message = responses.get(language, responses['en'])

        return {
            'message': message,
            'metadata': {'type': 'general_help'}
        }

    def _format_recommendations_message(self, recommendations, category, language):
        """Format recommendations into a readable message"""
        if not recommendations:
            no_results = {
                'en': f"Sorry, I couldn't find any {category} recommendations near your hotel at the moment.",
                'hi': f"क्षमा करें, मुझे इस समय आपके होटल के पास कोई {category} सुझाव नहीं मिल सके।",
                'es': f"Lo siento, no pude encontrar recomendaciones de {category} cerca de tu hotel en este momento.",
                'fr': f"Désolé, je n'ai pas pu trouver de recommandations de {category} près de votre hôtel pour le moment."
            }
            return no_results.get(language, no_results['en'])

        headers = {
            'en': f"Here are the top {category} recommendations near your hotel:",
            'hi': f"यहाँ आपके होटल के पास के शीर्ष {category} सुझाव हैं:",
            'es': f"Aquí están las mejores recomendaciones de {category} cerca de tu hotel:",
            'fr': f"Voici les meilleures recommandations de {category} près de votre hôtel:"
        }

        message = headers.get(language, headers['en']) + "\n\n"

        for i, rec in enumerate(recommendations[:5], 1):
            message += f"{i}. **{rec.get('name', 'Unknown')}**\n"
            if rec.get('rating'):
                message += f"   ⭐ Rating: {rec['rating']}/5\n"
            if rec.get('distance'):
                message += f"   📍 Distance: {rec['distance']} km\n"
            if rec.get('address'):
                message += f"   📍 Address: {rec['address']}\n"
            if rec.get('phone'):
                message += f"   📞 Phone: {rec['phone']}\n"
            message += "\n"

        return message

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

    def _add_message(self, session_id, message_type, content, metadata=None):
        """Add a message to the chat session"""
        message = ChatMessage(
            session_id=session_id,
            message_type=message_type,
            content=content,
            message_metadata=metadata
        )

        db.session.add(message)
        db.session.commit()

        return message

    def _get_session_messages(self, session_id):
        """Get all messages for a chat session"""
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
        return [message.to_dict() for message in messages]

    def get_chat_history(self, session_id):
        """Get chat history for a session"""
        try:
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if not chat_session:
                raise ValueError(f"Chat session {session_id} not found")

            return {
                'session_id': session_id,
                'booking': chat_session.booking.to_dict(),
                'messages': self._get_session_messages(chat_session.id),
                'language': chat_session.guest_language
            }

        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            raise
