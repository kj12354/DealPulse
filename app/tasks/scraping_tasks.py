import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.config import settings
from app import crud
from app.adapters.factory import adapter_factory

logger = logging.getLogger(__name__)

# Create database session for background tasks
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def scrape_product_price(product_id: int) -> dict:
    """
    Scrape price for a single product
    
    Args:
        product_id: ID of the product to scrape
        
    Returns:
        Dict with status and results
    """
    db = SessionLocal()
    try:
        # Get product
        product = crud.get_product(db, product_id)
        if not product:
            return {"status": "error", "message": f"Product {product_id} not found"}
        
        # Scrape current price
        product_info = adapter_factory.get_product_info(product.url)
        if not product_info:
            logger.warning(f"Failed to scrape price for product {product_id}: {product.url}")
            return {"status": "error", "message": f"Failed to scrape price for {product.name}"}
        
        # Store new price
        price_entry = crud.create_price_entry(db, product_id, product_info.price)
        
        # Update product name if it changed
        if product_info.name != product.name:
            crud.update_product(db, product_id, name=product_info.name)
        
        logger.info(f"Successfully scraped price for {product.name}: ${product_info.price}")
        
        return {
            "status": "success",
            "product_id": product_id,
            "product_name": product.name,
            "price": product_info.price,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error scraping product {product_id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def scrape_all_products() -> dict:
    """
    Scrape prices for all products that need updating
    
    Returns:
        Dict with summary of scraping results
    """
    db = SessionLocal()
    try:
        # Get products that need scraping
        products = crud.get_products_needing_scraping(db)
        
        if not products:
            logger.info("No products need scraping")
            return {"status": "success", "message": "No products need scraping", "scraped_count": 0}
        
        results = {
            "status": "success",
            "total_products": len(products),
            "scraped_count": 0,
            "failed_count": 0,
            "results": []
        }
        
        for product in products:
            result = scrape_product_price(product.id)
            results["results"].append(result)
            
            if result["status"] == "success":
                results["scraped_count"] += 1
            else:
                results["failed_count"] += 1
        
        logger.info(f"Scraping complete: {results['scraped_count']} successful, {results['failed_count']} failed")
        return results
        
    except Exception as e:
        logger.error(f"Error in scrape_all_products: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def schedule_scraping_jobs():
    """Schedule scraping jobs for all products"""
    from .redis_client import scraping_queue
    
    db = SessionLocal()
    try:
        products = crud.get_products_needing_scraping(db)
        
        job_ids = []
        for product in products:
            job = scraping_queue.enqueue(
                scrape_product_price,
                product.id,
                job_timeout='5m'
            )
            job_ids.append(job.id)
        
        logger.info(f"Scheduled {len(job_ids)} scraping jobs")
        return {"status": "success", "scheduled_jobs": len(job_ids), "job_ids": job_ids}
        
    except Exception as e:
        logger.error(f"Error scheduling scraping jobs: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close() 