#!/usr/bin/env python3
"""
Sample data seeding script for DealPulse Lite
Run this script to populate the database with test data
"""

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app import models, crud
from app import schemas

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_sample_data():
    """Create sample users, products, and price history"""
    db = SessionLocal()
    
    try:
        print("Creating sample data...")
        
        # Create sample users
        users_data = [
            "john.doe@example.com",
            "jane.smith@example.com",
            "tech.enthusiast@example.com"
        ]
        
        users = []
        for email in users_data:
            user = crud.get_or_create_user(db, email)
            users.append(user)
            print(f"Created user: {user.email}")
        
        # Sample products data
        products_data = [
            {
                "name": "iPhone 15 Pro Max 256GB - Natural Titanium",
                "retailer": "Amazon",
                "url": "https://www.amazon.com/dp/B0CHX1W1XY",
                "user_id": users[0].id,
                "prices": [1199.99, 1149.99, 1199.99, 1129.99, 1099.99]  # Showing price drops
            },
            {
                "name": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
                "retailer": "Amazon", 
                "url": "https://www.amazon.com/dp/B09XS7JWHH",
                "user_id": users[0].id,
                "prices": [399.99, 379.99, 349.99, 329.99, 319.99]
            },
            {
                "name": "MacBook Air 13-inch M3 Chip 8-Core CPU",
                "retailer": "Amazon",
                "url": "https://www.amazon.com/dp/B0CX23V2ZK", 
                "user_id": users[1].id,
                "prices": [1099.99, 1099.99, 1049.99, 1099.99, 999.99]
            },
            {
                "name": "Nintendo Switch OLED Console",
                "retailer": "Amazon",
                "url": "https://www.amazon.com/dp/B098RKWHHZ",
                "user_id": users[1].id,
                "prices": [349.99, 349.99, 329.99, 309.99, 289.99]
            },
            {
                "name": "Samsung 65\" 4K Smart TV",
                "retailer": "Amazon",
                "url": "https://www.amazon.com/dp/B0BTKJZPZP",
                "user_id": users[2].id,
                "prices": [599.99, 579.99, 549.99, 599.99, 499.99]
            },
            {
                "name": "Dyson V15 Detect Absolute Vacuum",
                "retailer": "Amazon", 
                "url": "https://www.amazon.com/dp/B08V7DLG2J",
                "user_id": users[2].id,
                "prices": [749.99, 699.99, 649.99, 629.99, 599.99]
            }
        ]
        
        # Create products and price history
        for product_data in products_data:
            prices = product_data.pop('prices')
            
            # Create product
            product_create = schemas.ProductCreate(**product_data)
            product = crud.create_product(db, product_create)
            print(f"Created product: {product.name}")
            
            # Create price history (oldest to newest)
            for i, price in enumerate(prices):
                price_entry = crud.create_price_entry(db, product.id, price)
                # Artificially set different dates for price history
                import datetime
                price_entry.date = datetime.datetime.utcnow() - datetime.timedelta(days=len(prices)-i-1)
                db.commit()
            
            print(f"  Added {len(prices)} price entries")
        
        print("\nSample data created successfully!")
        print(f"Created {len(users)} users")
        print(f"Created {len(products_data)} products")
        print(f"Created {sum(len(p['prices']) for p in products_data)} price entries")
        
        # Print summary
        print("\n" + "="*50)
        print("SAMPLE DATA SUMMARY")
        print("="*50)
        
        all_products = crud.get_all_products(db)
        for product in all_products:
            latest_price = crud.get_latest_price(db, product.id)
            avg_price = crud.get_average_price(db, product.id, days=30)
            
            print(f"\n📱 {product.name}")
            print(f"   Retailer: {product.retailer}")
            print(f"   User: {product.user.email}")
            print(f"   Current Price: ${latest_price.price:.2f}")
            if avg_price:
                print(f"   30-day Average: ${avg_price:.2f}")
                drop_percent = ((avg_price - latest_price.price) / avg_price) * 100
                if drop_percent > 0:
                    print(f"   💰 Price Drop: {drop_percent:.1f}%")
        
        print("\n" + "="*50)
        print("Ready to test! Try these endpoints:")
        print("- GET  http://localhost:8000/api/v1/watchlist")
        print("- GET  http://localhost:8000/api/v1/products/1")
        print("- GET  http://localhost:8000/api/v1/prices/1")
        print("- GET  http://localhost:8000/docs (API documentation)")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Create all tables first
    print("Creating database tables...")
    models.Base.metadata.create_all(bind=engine)
    
    # Create sample data
    create_sample_data() 