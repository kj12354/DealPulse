# DealPulse Lite

A deployable price monitoring service built with FastAPI that tracks product prices from multiple retailers and sends email alerts when prices drop significantly.

## Features

- 🔍 **Multi-Retailer Support**: Track products from Amazon, eBay, Walmart, and more
- 📊 **Price History**: Store and visualize historical price data
- 📧 **Smart Alerts**: Email notifications when prices drop >10% below 30-day average
- 🔄 **Automated Scraping**: Daily background jobs to update prices
- 🐳 **Docker Ready**: Easy deployment with Docker Compose
- 🧪 **Well Tested**: Comprehensive test suite with pytest

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   FastAPI       │    │     Redis       │    │   PostgreSQL    │
│   Web API       │◄──►│   Job Queue     │    │   Database      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       ▲
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │                 │              │
         └─────────────►│   RQ Worker     │──────────────┘
                        │   Background    │
                        │   Jobs          │
                        └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │   SendGrid      │
                        │   Email API     │
                        │                 │
                        └─────────────────┘
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/v1/products` - Add a product to track
- `GET /api/v1/watchlist` - List all tracked products
- `GET /api/v1/products/{id}` - Get product details with price history
- `GET /api/v1/prices/{id}` - Get price history for a product
- `DELETE /api/v1/products/{id}` - Remove product from tracking

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- SendGrid API key (for email alerts)

### Option 1: Docker Compose (Recommended)

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd Amazon_Tracker
   cp env.example .env
   ```

2. **Update environment variables**:
   ```bash
   # Edit .env file with your configuration
   SENDGRID_API_KEY=your_sendgrid_api_key_here
   FROM_EMAIL=noreply@yourdomain.com
   ```

3. **Start all services**:
   ```bash
   docker-compose up --build
   ```

4. **Access the application**:
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Database: localhost:5432
   - Redis: localhost:6379

### Option 2: Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and Redis**:
   ```bash
   # Using Docker for databases only
   docker run -d --name postgres -p 5432:5432 \
     -e POSTGRES_DB=dealpulse_db \
     -e POSTGRES_USER=dealpulse \
     -e POSTGRES_PASSWORD=password \
     postgres:15-alpine

   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

3. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Start the API server**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Start the worker** (in separate terminal):
   ```bash
   python worker.py
   ```

## Usage Examples

### Add a Product to Track

```bash
curl -X POST "http://localhost:8000/api/v1/products" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.amazon.com/dp/B08N5WRWNW",
       "user_email": "user@example.com"
     }'
```

### Get Your Watchlist

```bash
curl "http://localhost:8000/api/v1/watchlist"
```

### View Price History

```bash
curl "http://localhost:8000/api/v1/prices/1"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://dealpulse:password@localhost:5432/dealpulse_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SENDGRID_API_KEY` | SendGrid API key for emails | Required for email alerts |
| `FROM_EMAIL` | Email address for sending alerts | `noreply@dealpulse.com` |
| `SECRET_KEY` | Application secret key | `dev-secret-key-change-in-production` |
| `DEBUG` | Enable debug mode | `True` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `WORKER_CONCURRENCY` | Number of worker processes | `2` |
| `SCRAPING_INTERVAL_HOURS` | Hours between price checks | `24` |

## Scraping Adapters

The system uses a flexible adapter pattern for scraping different websites:

### 1. JSON-LD Adapter
- Extracts structured data (JSON-LD, microdata, RDFa)
- Best for: Amazon, eBay, major e-commerce sites
- Most reliable when available

### 2. HTML Adapter
- Parses HTML using BeautifulSoup
- Fallback for sites without structured data
- Uses multiple CSS selectors and patterns

### Adding Custom Adapters

```python
from app.adapters.base import BaseAdapter, ProductInfo

class CustomAdapter(BaseAdapter):
    def supports_url(self, url: str) -> bool:
        return "customsite.com" in url
    
    def get_product_info(self, url: str) -> ProductInfo:
        # Your scraping logic here
        return ProductInfo(name="Product Name", price=29.99)

# Register the adapter
from app.adapters.factory import adapter_factory
adapter_factory.add_adapter(CustomAdapter(), priority=0)
```

## Background Jobs

### Price Scraping
- Runs daily to update product prices
- Processes products that haven't been updated in 23+ hours
- Uses RQ (Redis Queue) for job management

### Email Alerts
- Sends daily digest emails
- Only alerts when price drops >10% below 30-day average
- HTML and plain text email formats

### Manual Job Triggers

```python
# Scrape all products now
from app.tasks.scraping_tasks import scrape_all_products
result = scrape_all_products()

# Send price alerts now
from app.tasks.email_tasks import send_daily_price_alerts
result = send_daily_price_alerts()
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_adapters.py -v
```

### Test Coverage

- ✅ Adapter scraping logic with mock HTML
- ✅ Price calculation functions
- ✅ API endpoint validation
- ✅ Database operations
- ✅ Error handling scenarios

## Monitoring and Logs

### Application Logs
```bash
# View API logs
docker-compose logs -f api

# View worker logs
docker-compose logs -f worker

# View all logs
docker-compose logs -f
```

### Health Checks
- API: `GET /health`
- Database: Built into docker-compose
- Redis: Built into docker-compose

### Metrics to Monitor
- Scraping success/failure rates
- Email delivery rates
- Queue length and processing times
- Database connection pool usage

## Production Deployment

### Security Considerations

1. **Change default passwords**:
   ```bash
   # Generate secure passwords for production
   openssl rand -base64 32  # For SECRET_KEY
   ```

2. **Use environment-specific configs**:
   ```bash
   # Production settings
   DEBUG=False
   LOG_LEVEL=WARNING
   ```

3. **Secure database access**:
   - Use strong passwords
   - Enable SSL connections
   - Restrict network access

### Scaling

1. **Horizontal scaling**:
   ```yaml
   # Scale workers in docker-compose.yml
   worker:
     deploy:
       replicas: 5
   ```

2. **Database optimization**:
   - Add indexes for frequent queries
   - Consider read replicas for large datasets
   - Archive old price history data

3. **Caching**:
   - Redis for session/cache data
   - CDN for static assets
   - Application-level caching for expensive operations

### Backup Strategy

```bash
# Database backup
docker exec postgres pg_dump -U dealpulse dealpulse_db > backup.sql

# Redis backup (if needed)
docker exec redis redis-cli SAVE
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Common Issues

1. **Scraping failures**:
   - Check if website structure changed
   - Verify adapter selectors
   - Monitor rate limiting

2. **Email not sending**:
   - Verify SendGrid API key
   - Check FROM_EMAIL domain verification
   - Review SendGrid activity logs

3. **Database connection errors**:
   - Ensure PostgreSQL is running
   - Check connection string format
   - Verify network connectivity

4. **Redis connection issues**:
   - Ensure Redis is running
   - Check Redis URL format
   - Monitor memory usage

### Debug Mode

Enable detailed logging:
```bash
export DEBUG=True
export LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Create an issue in the repository
- Check existing documentation
- Review logs for error details 