import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app import models

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Generator[sessionmaker, None, None]:
    """Create test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_user(db_session) -> models.User:
    """Create a sample user for testing"""
    user = models.User(email="test@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_product(db_session, sample_user) -> models.Product:
    """Create a sample product for testing"""
    product = models.Product(
        name="Test Product",
        retailer="Amazon",
        url="https://www.amazon.com/test-product",
        user_id=sample_user.id
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product 