from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis
from config.config import Config

# Initialize database
db = SQLAlchemy()
migrate = Migrate()

# Initialize Redis for caching
redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    migrate.init_app(app, db)
    
    with app.app_context():
        db.create_all()

def get_redis_client():
    """Get Redis client instance"""
    return redis_client
