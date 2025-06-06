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
# MapMyIndia API (Primary - Free)
MAPMYINDIA_API_KEY=your_mapmyindia_api_key_here
MAPMYINDIA_CLIENT_ID=your_mapmyindia_client_id_here
MAPMYINDIA_CLIENT_SECRET=your_mapmyindia_client_secret_here

# Google Places API (Fallback - Optional)
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here

# OpenAI API (Optional)
OPENAI_API_KEY=your_openai_api_key_here

# Webhook Security
WEBHOOK_SECRET=your_webhook_secret_here

# Database Configuration
DATABASE_URL=sqlite:///treebo_chatbot.db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# External Booking Search API
BOOKING_SEARCH_API_URL=https://growth.treebo.be/growth-realization/custom_message/search_booking_by_phone/
BOOKING_SEARCH_API_AUTH=your_booking_api_auth_token_here
```

**⚠️ Security Note:**
- Never commit your `.env` file to version control
- The `.env.example` file contains placeholder values only
- Replace all placeholder values with your actual API keys

**Getting MapMyIndia API Keys (Free):**
1. Visit [MapMyIndia Developer Portal](https://www.mapmyindia.com/api/)
2. Sign up for a free account
3. Create a new project and get your API key, Client ID, and Client Secret
4. MapMyIndia provides free tier with generous limits for Indian locations

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

## Usage

### Web Interface

1. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

2. **Simulate a booking event** using the provided buttons:
   - Click "Sample Booking 1" or "Sample Booking 2" for predefined events
   - Use "Custom Event" to test with your own JSON structure

3. **Start chatting** with the recommendation bot after the booking is processed

4. **Ask for recommendations** like:
   - "What restaurants are nearby?"
   - "Show me tourist attractions"
   - "Any events happening today?"
   - "Where can I go shopping?"

### Production Integration

In production, bookings are created by external services that send booking events to the webhook endpoint. The UI booking creation is disabled and replaced with event simulation for testing purposes.

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

### External Booking Created Event (New Format)

The system now handles complex booking events from external services with the following structure:

```json
{
  "message_id": "EVT-050625-1121-9199-5649",
  "generated_at": "2025-06-05T16:51:39.745904+05:30",
  "events": [
    {
      "entity_name": "booking",
      "payload": {
        "booking_id": "3387-8193-5572",
        "reference_number": "TRB-17491224854750",
        "hotel_id": "0016581",
        "status": "reserved",
        "checkin_date": "2025-06-05T14:00:00+05:30",
        "checkout_date": "2025-06-06T12:00:00+05:30",
        "source": {
          "channel_code": "direct",
          "application_code": "website",
          "subchannel_code": "website-direct"
        },
        "customers": [
          {
            "customer_id": "1",
            "first_name": "Vivek",
            "last_name": "Yadav",
            "email": "vivekyadav.9991+11@gmail.com",
            "phone": {
              "number": "8904348449",
              "country_code": "+91"
            },
            "is_primary": false,
            "dummy": false
          }
        ]
      }
    },
    {
      "entity_name": "bill",
      "payload": {
        "vendor_details": {
          "hotel_name": "Treebo Club Worldtree Staging",
          "address": {
            "field_1": "#204, Prashant Extension, Near Hope Farm Whitefield",
            "city": "Bangalore",
            "state": "Karnataka"
          }
        }
      }
    }
  ],
  "event_type": "booking.created"
}
```

### Legacy Booking Created Event (Backward Compatible)

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

## MapMyIndia Integration

This system now uses **MapMyIndia API** as the primary mapping service, providing several advantages:

### Benefits:
- **Free Tier**: Generous free usage limits for Indian locations
- **Local Expertise**: Better coverage and accuracy for Indian addresses and landmarks
- **Cost Effective**: No charges for basic geocoding and place search operations
- **Indian Focus**: Optimized for Indian geography and local businesses

### Features:
- **Geocoding**: Convert addresses to coordinates and vice versa
- **Nearby Search**: Find restaurants, attractions, shopping centers, etc.
- **Place Details**: Get additional information about places
- **Fallback Support**: Automatically falls back to Google Places API if needed

### API Coverage:
- Geocoding and Reverse Geocoding
- Nearby Places Search with categories
- Place Details and Information
- Distance Calculations

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
| `MAPMYINDIA_API_KEY` | MapMyIndia API key (Primary) | Required |
| `MAPMYINDIA_CLIENT_ID` | MapMyIndia Client ID | Required |
| `MAPMYINDIA_CLIENT_SECRET` | MapMyIndia Client Secret | Required |
| `GOOGLE_PLACES_API_KEY` | Google Places API key (Fallback) | Optional |
| `WEBHOOK_SECRET` | Webhook signature verification | Optional |
| `DEFAULT_LANGUAGE` | Default guest language | `en` |
| `RECOMMENDATION_RADIUS` | Search radius in meters | `5000` |

## Monitoring and Logging

- Application logs are written to stdout
- Health check endpoint: `/health`
- System statistics: `/admin/stats`
- Redis monitoring available on port 6379

## Security

### Environment Variables Security
- **`.env` file**: Contains real API keys and secrets, never committed to git
- **`.env.example` file**: Template with placeholder values, safe to commit
- **`.gitignore`**: Ensures `.env` file is never accidentally committed
- **Setup process**: Copy `.env.example` to `.env` and replace placeholders

### Application Security
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
