import logging
from googletrans import Translator
from langdetect import detect
from config.config import Config
from config.database import get_redis_client
import json

logger = logging.getLogger(__name__)

class TranslationService:
    """Service for handling multi-language translation"""
    
    def __init__(self):
        self.translator = Translator()
        self.redis_client = get_redis_client()
        self.supported_languages = Config.SUPPORTED_LANGUAGES
        self.default_language = Config.DEFAULT_LANGUAGE
    
    def detect_language(self, text):
        """Detect the language of given text"""
        try:
            detected_lang = detect(text)
            if detected_lang in self.supported_languages:
                return detected_lang
            return self.default_language
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return self.default_language
    
    def translate_text(self, text, target_language, source_language='auto'):
        """Translate text to target language"""
        if target_language == source_language or target_language == 'en':
            return text
        
        # Check cache first
        cache_key = f"translation:{hash(text)}:{source_language}:{target_language}"
        cached_translation = self.redis_client.get(cache_key)
        
        if cached_translation:
            return cached_translation
        
        try:
            result = self.translator.translate(
                text, 
                src=source_language, 
                dest=target_language
            )
            translated_text = result.text
            
            # Cache the translation for 24 hours
            self.redis_client.setex(cache_key, 86400, translated_text)
            
            return translated_text
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text  # Return original text if translation fails
    
    def translate_recommendations(self, recommendations, target_language):
        """Translate recommendation data to target language"""
        if target_language == 'en':
            return recommendations
        
        translated_recommendations = []
        
        for rec in recommendations:
            try:
                translated_rec = rec.copy()
                
                # Translate name and description
                if 'name' in rec:
                    translated_rec['name'] = self.translate_text(
                        rec['name'], target_language
                    )
                
                if 'description' in rec:
                    translated_rec['description'] = self.translate_text(
                        rec['description'], target_language
                    )
                
                if 'category' in rec:
                    translated_rec['category'] = self.translate_text(
                        rec['category'], target_language
                    )
                
                # Translate reviews if available
                if 'reviews' in rec and rec['reviews']:
                    translated_reviews = []
                    for review in rec['reviews'][:3]:  # Translate only first 3 reviews
                        translated_review = self.translate_text(
                            review, target_language
                        )
                        translated_reviews.append(translated_review)
                    translated_rec['reviews'] = translated_reviews
                
                translated_recommendations.append(translated_rec)
                
            except Exception as e:
                logger.error(f"Failed to translate recommendation: {e}")
                translated_recommendations.append(rec)  # Add original if translation fails
        
        return translated_recommendations
    
    def get_welcome_message(self, guest_name, hotel_name, language='en'):
        """Get welcome message in specified language"""
        messages = {
            'en': f"Hello {guest_name}! Welcome to {hotel_name}. I'm your personal travel assistant. I can help you discover amazing restaurants, attractions, and events near your hotel. What would you like to explore?",
            'hi': f"नमस्ते {guest_name}! {hotel_name} में आपका स्वागत है। मैं आपका व्यक्तिगत यात्रा सहायक हूं। मैं आपको आपके होटल के पास के अद्भुत रेस्तरां, आकर्षण और कार्यक्रमों की खोज में मदद कर सकता हूं। आप क्या खोजना चाहेंगे?",
            'es': f"¡Hola {guest_name}! Bienvenido a {hotel_name}. Soy tu asistente personal de viajes. Puedo ayudarte a descubrir restaurantes increíbles, atracciones y eventos cerca de tu hotel. ¿Qué te gustaría explorar?",
            'fr': f"Bonjour {guest_name}! Bienvenue à {hotel_name}. Je suis votre assistant de voyage personnel. Je peux vous aider à découvrir d'incroyables restaurants, attractions et événements près de votre hôtel. Que souhaitez-vous explorer?",
            'de': f"Hallo {guest_name}! Willkommen im {hotel_name}. Ich bin Ihr persönlicher Reiseassistent. Ich kann Ihnen helfen, erstaunliche Restaurants, Sehenswürdigkeiten und Veranstaltungen in der Nähe Ihres Hotels zu entdecken. Was möchten Sie erkunden?",
            'ja': f"こんにちは{guest_name}さん！{hotel_name}へようこそ。私はあなたの個人旅行アシスタントです。ホテル近くの素晴らしいレストラン、観光地、イベントを見つけるお手伝いをします。何を探索したいですか？",
            'ko': f"안녕하세요 {guest_name}님! {hotel_name}에 오신 것을 환영합니다. 저는 당신의 개인 여행 도우미입니다. 호텔 근처의 멋진 레스토랑, 관광지, 이벤트를 찾는 데 도움을 드릴 수 있습니다. 무엇을 탐험하고 싶으신가요?",
            'zh': f"你好{guest_name}！欢迎来到{hotel_name}。我是您的个人旅行助手。我可以帮助您发现酒店附近的精彩餐厅、景点和活动。您想探索什么？"
        }
        
        return messages.get(language, messages['en'])
    
    def get_category_options(self, language='en'):
        """Get category options in specified language"""
        options = {
            'en': {
                'restaurants': '🍽️ Restaurants & Dining',
                'sightseeing': '🏛️ Sightseeing & Attractions',
                'events': '🎭 Events & Entertainment',
                'shopping': '🛍️ Shopping',
                'nightlife': '🌃 Nightlife'
            },
            'hi': {
                'restaurants': '🍽️ रेस्तरां और भोजन',
                'sightseeing': '🏛️ दर्शनीय स्थल और आकर्षण',
                'events': '🎭 कार्यक्रम और मनोरंजन',
                'shopping': '🛍️ खरीदारी',
                'nightlife': '🌃 रात्रि जीवन'
            },
            'es': {
                'restaurants': '🍽️ Restaurantes y Comida',
                'sightseeing': '🏛️ Turismo y Atracciones',
                'events': '🎭 Eventos y Entretenimiento',
                'shopping': '🛍️ Compras',
                'nightlife': '🌃 Vida Nocturna'
            },
            'fr': {
                'restaurants': '🍽️ Restaurants et Cuisine',
                'sightseeing': '🏛️ Tourisme et Attractions',
                'events': '🎭 Événements et Divertissement',
                'shopping': '🛍️ Shopping',
                'nightlife': '🌃 Vie Nocturne'
            }
        }
        
        return options.get(language, options['en'])
