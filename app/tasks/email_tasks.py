import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import settings
from app import crud, models

logger = logging.getLogger(__name__)

# Create database session for background tasks
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def calculate_price_drop_percentage(current_price: float, average_price: float) -> float:
    """Calculate price drop percentage"""
    if average_price <= 0:
        return 0.0
    return ((average_price - current_price) / average_price) * 100


def get_products_with_price_drops() -> List[Dict[str, Any]]:
    """Get products with significant price drops (> 10% below 30-day average)"""
    db = SessionLocal()
    try:
        products = crud.get_all_products(db)
        price_drops = []
        
        for product in products:
            # Get latest price
            latest_price = crud.get_latest_price(db, product.id)
            if not latest_price:
                continue
            
            # Get 30-day average
            avg_price = crud.get_average_price(db, product.id, days=30)
            if not avg_price:
                continue
            
            # Check if current price is significantly lower (more than 10% drop)
            drop_threshold = avg_price * 0.9  # 10% drop threshold
            if latest_price.price < drop_threshold:
                drop_percentage = calculate_price_drop_percentage(latest_price.price, avg_price)
                
                price_drops.append({
                    'product': product,
                    'current_price': latest_price.price,
                    'average_price': avg_price,
                    'drop_percentage': drop_percentage,
                    'savings': avg_price - latest_price.price,
                    'latest_price_date': latest_price.date
                })
        
        return price_drops
        
    except Exception as e:
        logger.error(f"Error getting products with price drops: {e}")
        return []
    finally:
        db.close()


def send_price_drop_email(user_email: str, price_drops: List[Dict[str, Any]]) -> dict:
    """
    Send price drop notification email to user
    
    Args:
        user_email: Email address to send to
        price_drops: List of products with price drops
        
    Returns:
        Dict with status and message
    """
    if not settings.SENDGRID_API_KEY:
        logger.warning("SendGrid API key not configured, skipping email")
        return {"status": "skipped", "message": "SendGrid API key not configured"}
    
    if not price_drops:
        return {"status": "skipped", "message": "No price drops to report"}
    
    try:
        # Create email content
        html_content = create_price_drop_email_html(price_drops)
        plain_content = create_price_drop_email_text(price_drops)
        
        # Create email message
        message = Mail(
            from_email=settings.FROM_EMAIL,
            to_emails=user_email,
            subject=f"🎉 Price Drops Alert - {len(price_drops)} Product{'s' if len(price_drops) > 1 else ''} on Sale!",
            html_content=html_content,
            plain_text_content=plain_content
        )
        
        # Send email
        sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"Price drop email sent to {user_email} - Status: {response.status_code}")
        
        return {
            "status": "success",
            "message": f"Email sent to {user_email}",
            "status_code": response.status_code,
            "products_count": len(price_drops)
        }
        
    except Exception as e:
        logger.error(f"Error sending price drop email to {user_email}: {e}")
        return {"status": "error", "message": str(e)}


def create_price_drop_email_html(price_drops: List[Dict[str, Any]]) -> str:
    """Create HTML email content for price drops"""
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2c5aa0;">🎉 Price Drop Alert!</h1>
            <p>Great news! We found <strong>{len(price_drops)}</strong> product{'s' if len(price_drops) > 1 else ''} with significant price drops:</p>
            
            <div style="margin: 20px 0;">
    """
    
    for drop in price_drops:
        product = drop['product']
        html += f"""
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; background-color: #f9f9f9;">
                    <h3 style="margin-top: 0; color: #2c5aa0;">{product.name}</h3>
                    <p><strong>Retailer:</strong> {product.retailer}</p>
                    <p style="font-size: 18px;">
                        <span style="color: #e74c3c; font-weight: bold;">Now: ${drop['current_price']:.2f}</span>
                        <span style="color: #666; text-decoration: line-through; margin-left: 10px;">Was: ${drop['average_price']:.2f}</span>
                    </p>
                    <p style="color: #27ae60; font-weight: bold;">
                        💰 Save ${drop['savings']:.2f} ({drop['drop_percentage']:.1f}% off!)
                    </p>
                    <a href="{product.url}" style="background-color: #2c5aa0; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Product</a>
                </div>
        """
    
    html += """
            </div>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            
            <p style="font-size: 12px; color: #666;">
                This email was sent by DealPulse Lite. Prices are updated daily and may have changed since this alert was sent.
            </p>
        </div>
    </body>
    </html>
    """
    
    return html


def create_price_drop_email_text(price_drops: List[Dict[str, Any]]) -> str:
    """Create plain text email content for price drops"""
    text = f"🎉 Price Drop Alert!\n\n"
    text += f"Great news! We found {len(price_drops)} product{'s' if len(price_drops) > 1 else ''} with significant price drops:\n\n"
    
    for i, drop in enumerate(price_drops, 1):
        product = drop['product']
        text += f"{i}. {product.name}\n"
        text += f"   Retailer: {product.retailer}\n"
        text += f"   Now: ${drop['current_price']:.2f} (was ${drop['average_price']:.2f})\n"
        text += f"   💰 Save ${drop['savings']:.2f} ({drop['drop_percentage']:.1f}% off!)\n"
        text += f"   Link: {product.url}\n\n"
    
    text += "---\n"
    text += "This email was sent by DealPulse Lite. Prices are updated daily and may have changed since this alert was sent.\n"
    
    return text


def send_daily_price_alerts() -> dict:
    """
    Send daily price alert emails to all users with price drops
    
    Returns:
        Dict with summary of email sending results
    """
    db = SessionLocal()
    try:
        # Get all price drops
        price_drops = get_products_with_price_drops()
        
        if not price_drops:
            logger.info("No price drops found for daily alerts")
            return {"status": "success", "message": "No price drops found", "emails_sent": 0}
        
        # Group price drops by user
        user_price_drops = {}
        for drop in price_drops:
            user_email = drop['product'].user.email
            if user_email not in user_price_drops:
                user_price_drops[user_email] = []
            user_price_drops[user_email].append(drop)
        
        # Send emails to each user
        results = {
            "status": "success",
            "total_price_drops": len(price_drops),
            "users_notified": 0,
            "emails_sent": 0,
            "emails_failed": 0,
            "results": []
        }
        
        for user_email, user_drops in user_price_drops.items():
            result = send_price_drop_email(user_email, user_drops)
            results["results"].append({
                "user_email": user_email,
                "products_count": len(user_drops),
                "result": result
            })
            
            if result["status"] == "success":
                results["emails_sent"] += 1
                results["users_notified"] += 1
            elif result["status"] == "error":
                results["emails_failed"] += 1
        
        logger.info(f"Daily alerts complete: {results['emails_sent']} emails sent, {results['emails_failed']} failed")
        return results
        
    except Exception as e:
        logger.error(f"Error sending daily price alerts: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def schedule_daily_alerts():
    """Schedule daily price alert emails"""
    from .redis_client import email_queue
    
    try:
        job = email_queue.enqueue(
            send_daily_price_alerts,
            job_timeout='10m'
        )
        
        logger.info(f"Scheduled daily price alerts job: {job.id}")
        return {"status": "success", "job_id": job.id}
        
    except Exception as e:
        logger.error(f"Error scheduling daily alerts: {e}")
        return {"status": "error", "message": str(e)} 