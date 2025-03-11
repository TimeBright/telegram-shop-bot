"""Database models for the shop module."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import logging

Base = declarative_base()

class Product(Base):
    """Model for products in the shop."""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    specifications = Column(JSON)  # Характеристики товара в формате JSON
    price = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # Категория товара: 'cosmetics' или 'electronics'
    available = Column(Boolean, default=True)
    payment_link = Column(String)  # Ссылка для оплаты
    payment_qr = Column(String)    # QR код для оплаты (URL или base64)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь с фотографиями
    photos = relationship("ProductPhoto", back_populates="product", cascade="all, delete-orphan")

class ProductPhoto(Base):
    """Model for product photos."""
    __tablename__ = 'product_photos'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    photo_url = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)  # Порядок сортировки
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь с продуктом
    product = relationship("Product", back_populates="photos")

class Order(Base):
    """Model for orders."""
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)  # Telegram user ID
    customer_name = Column(String, nullable=False)  # Имя заказчика
    customer_phone = Column(String, nullable=False)  # Телефон заказчика
    delivery_address = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    payment_status = Column(String, default='pending')  # pending, paid, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь с товарами в заказе
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    """Model for items in order."""
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)  # Цена на момент заказа
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class Cart(Base):
    """Model for user's shopping cart."""
    __tablename__ = 'carts'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)  # Telegram user ID
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")

class ProductSuggestion(Base):
    """Model for product suggestions from users."""
    __tablename__ = 'product_suggestions'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)  # Telegram user ID
    suggestion = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserQuestion(Base):
    """Model for user questions."""
    __tablename__ = 'user_questions'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)  # Telegram user ID
    question = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminUser(Base):
    """Model for admin users."""
    __tablename__ = 'admin_users'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, unique=True)  # Telegram user ID
    username = Column(String, nullable=False, unique=True)
    email = Column(String, unique=True)  # Email field
    password_hash = Column(String)  # Password storage
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)  # Email verification status
    verification_code = Column(String)  # For storing one-time verification code
    verification_code_expires = Column(DateTime)  # Expiration time for verification code
    created_at = Column(DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Set hashed password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if password matches."""
        return check_password_hash(self.password_hash, password)