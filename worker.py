#!/usr/bin/env python3
"""
RQ Worker script for DealPulse Lite
Processes background jobs for scraping and email alerts
"""

import os
import sys
import logging
from rq import Worker, Connection
from app.tasks.redis_client import redis_conn
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run the RQ worker"""
    queues = ['scraping', 'email', 'default']
    
    logger.info(f"Starting RQ worker for queues: {queues}")
    logger.info(f"Worker concurrency: {settings.WORKER_CONCURRENCY}")
    
    with Connection(redis_conn):
        worker = Worker(queues)
        worker.work()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1) 