import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'treebo-chatbot-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///treebo_chatbot.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis configuration for caching
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # External API configurations
    # Google Places API for location services
    GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')

    # Other APIs
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Chatbot configuration
    DEFAULT_LANGUAGE = 'en'
    SUPPORTED_LANGUAGES = ['en', 'hi', 'es', 'fr', 'de', 'ja', 'ko', 'zh']
    
    # Recommendation settings
    RECOMMENDATION_RADIUS = 5000  # 5km radius
    MAX_RECOMMENDATIONS_PER_CATEGORY = 5
    CACHE_TIMEOUT = 3600  # 1 hour
    
    # Webhook security
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET') or 'treebo-webhook-secret'

    # External Booking Search API
    BOOKING_SEARCH_API_URL = os.environ.get('BOOKING_SEARCH_API_URL') or 'https://growth.treebo.be/growth-realization/custom_message/search_booking_by_phone/'
    BOOKING_SEARCH_API_AUTH = os.environ.get('BOOKING_SEARCH_API_AUTH') or 'Basic c3VfdXNlcjpFN3FVazl1X2ZxOF9XQg=='

    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/1'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/1'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_treebo_chatbot.db'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
