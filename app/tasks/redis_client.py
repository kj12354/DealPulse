import redis
from rq import Queue
from app.config import settings

# Create Redis connection
redis_conn = redis.from_url(settings.REDIS_URL)

# Create RQ queues
default_queue = Queue('default', connection=redis_conn)
scraping_queue = Queue('scraping', connection=redis_conn)
email_queue = Queue('email', connection=redis_conn) 