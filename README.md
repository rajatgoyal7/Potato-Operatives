# Treebo Location-Specific Recommendation Chatbot

An event-driven chatbot system that provides location-specific recommendations (restaurants, sightseeing, events, etc.) to Treebo hotel guests when bookings are created. Features multi-lingual support for international travelers.

## Features

- **Event-Driven Architecture**: Listens for booking events via webhooks
- **Location-Based Recommendations**: Restaurants, attractions, events, shopping, nightlife
- **Multi-Language Support**: 8 languages (English, Hindi, Spanish, French, German, Japanese, Korean, Chinese)
- **Real-time Chat Interface**: Interactive conversation with guests
- **Intelligent Caching**: Redis and database caching for performance
- **Scalable Design**: Microservices architecture with Docker support

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Booking       │    │   Treebo        │    │   Guest         │
│   Service       │───▶│   Chatbot       │◀──▶│   Interface     │
│                 │    │   API           │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Recommendation│
                    │   Engine        │
                    │                 │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   External APIs │
                    │   (Google Places│
                    │   Foursquare)   │
                    └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Google Places API key
- (Optional) OpenAI API key for enhanced responses

### 1. Clone and Setup

```bash
git clone <repository-url>
cd treebo-chatbot
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your API keys:

```bash
GOOGLE_PLACES_API_KEY=your-google-places-api-key
OPENAI_API_KEY=your-openai-api-key
WEBHOOK_SECRET=your-webhook-secret
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- Main Flask application (port 5000)
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- Celery worker for background tasks

### 4. Test the System

```bash
# Health check
curl http://localhost:5000/health

# Create a test booking event
curl -X POST http://localhost:5000/webhook/booking \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "booking.created",
    "booking": {
      "booking_id": "TRB123456",
      "guest_name": "John Doe",
      "guest_email": "john@example.com",
      "hotel_name": "Treebo Trend Hotel",
      "hotel_location": "Connaught Place, New Delhi, India",
      "check_in_date": "2024-01-15",
      "check_out_date": "2024-01-17",
      "guest_language": "en"
    }
  }'
```

## API Endpoints

### Webhook Endpoints

- `POST /webhook/booking` - Receive booking events from external services

### Chat Endpoints

- `POST /chat/session` - Create new chat session
- `POST /chat/message` - Send message to chatbot
- `GET /chat/recommendations/{session_id}/{category}` - Get specific recommendations
- `GET /chat/history/{session_id}` - Get chat history

### Management Endpoints

- `GET /booking/{booking_id}` - Get booking information
- `GET /booking/{booking_id}/sessions` - Get all chat sessions for booking
- `GET /admin/stats` - Get system statistics
- `GET /health` - Health check

## Event Format

### Booking Created Event

```json
{
  "event_type": "booking.created",
  "booking": {
    "booking_id": "TRB123456",
    "guest_name": "John Doe",
    "guest_email": "john@example.com",
    "guest_phone": "+91-9876543210",
    "hotel_name": "Treebo Trend Hotel",
    "hotel_location": "Connaught Place, New Delhi, India",
    "check_in_date": "2024-01-15",
    "check_out_date": "2024-01-17",
    "guest_language": "en"
  }
}
```

## Supported Languages

- English (en)
- Hindi (hi)
- Spanish (es)
- French (fr)
- German (de)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)

## Recommendation Categories

- **Restaurants** - Local dining options with ratings and reviews
- **Sightseeing** - Tourist attractions, museums, parks
- **Events** - Local events, concerts, festivals
- **Shopping** - Malls, markets, shopping centers
- **Nightlife** - Bars, clubs, entertainment venues

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
export FLASK_APP=app.py
flask db init
flask db migrate
flask db upgrade

# Run application
python app.py
```

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
treebo-chatbot/
├── app.py                 # Main Flask application
├── config/
│   ├── config.py         # Configuration settings
│   └── database.py       # Database initialization
├── chatbot/
│   ├── __init__.py
│   ├── models.py         # Database models
│   ├── event_handler.py  # Event processing
│   ├── chatbot_service.py # Main chatbot logic
│   ├── recommendation_engine.py # Recommendation fetching
│   └── translation_service.py # Multi-language support
├── tests/                # Unit tests
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker services
├── Dockerfile           # Container definition
└── README.md           # This file
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `development` |
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///treebo_chatbot.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `GOOGLE_PLACES_API_KEY` | Google Places API key | Required |
| `WEBHOOK_SECRET` | Webhook signature verification | Optional |
| `DEFAULT_LANGUAGE` | Default guest language | `en` |
| `RECOMMENDATION_RADIUS` | Search radius in meters | `5000` |

## Monitoring and Logging

- Application logs are written to stdout
- Health check endpoint: `/health`
- System statistics: `/admin/stats`
- Redis monitoring available on port 6379

## Security

- Webhook signature verification using HMAC-SHA256
- Input validation on all endpoints
- SQL injection protection via SQLAlchemy ORM
- CORS enabled for web integration

## Scaling Considerations

- Horizontal scaling via multiple container instances
- Redis clustering for high availability
- Database read replicas for performance
- CDN for static assets
- Load balancer for traffic distribution

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation and logs
