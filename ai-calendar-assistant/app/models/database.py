"""SQLAlchemy ORM models for database schema management with Alembic.

These models define the database schema and are used by Alembic for migrations.
The actual data access currently uses raw sqlite3 in analytics_service.py,
but this provides a structured definition for schema migrations.

Usage:
    from app.models.database import Base, User, Action, Referral

    # For Alembic migrations, models are imported in alembic/env.py
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class User(Base):
    """User model - stores Telegram user information."""

    __tablename__ = "users"

    user_id = Column(String, primary_key=True, comment="Telegram user ID")
    chat_id = Column(Integer, nullable=False, comment="Telegram chat ID")
    username = Column(String, nullable=True, comment="Telegram username (without @)")
    first_name = Column(String, nullable=True, comment="User's first name")
    last_name = Column(String, nullable=True, comment="User's last name")
    first_seen = Column(DateTime, default=datetime.utcnow, comment="First interaction timestamp")
    last_seen = Column(DateTime, nullable=True, comment="Last interaction timestamp")
    is_active = Column(Integer, default=1, comment="1 if user is active, 0 otherwise")
    is_hidden_in_admin = Column(Integer, default=0, comment="1 if hidden from admin panel")
    referred_by = Column(String, nullable=True, comment="User ID who referred this user")
    referral_code = Column(String, nullable=True, index=True, comment="User's referral code")

    # Relationships
    actions = relationship("Action", back_populates="user")
    referrals_made = relationship(
        "Referral",
        foreign_keys="Referral.referrer_id",
        back_populates="referrer"
    )

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"


class Action(Base):
    """Action model - stores user activity and analytics."""

    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, comment="Telegram user ID")
    action_type = Column(String, nullable=False, comment="Type of action (message, event_create, etc.)")
    timestamp = Column(DateTime, default=datetime.utcnow, comment="When action occurred")
    details = Column(Text, nullable=True, comment="Action details (JSON or text)")
    event_id = Column(String, nullable=True, comment="Related calendar event ID")
    success = Column(Integer, default=1, comment="1 if action succeeded, 0 otherwise")
    error_message = Column(Text, nullable=True, comment="Error message if failed")
    is_test = Column(Integer, default=0, comment="1 if this is from a test user")

    # LLM usage tracking
    input_tokens = Column(Integer, nullable=True, comment="LLM input tokens used")
    output_tokens = Column(Integer, nullable=True, comment="LLM output tokens used")
    total_tokens = Column(Integer, nullable=True, comment="Total LLM tokens used")
    cost_rub = Column(Float, nullable=True, comment="LLM cost in rubles")
    llm_model = Column(String, nullable=True, comment="LLM model used (yandexgpt-lite, etc.)")

    # Relationships
    user = relationship("User", back_populates="actions")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_actions_user_timestamp", "user_id", "timestamp"),
        Index("idx_actions_timestamp", "timestamp"),
        Index("idx_actions_type", "action_type"),
        Index("idx_actions_success", "success"),
    )

    def __repr__(self):
        return f"<Action(id={self.id}, user_id={self.user_id}, type={self.action_type})>"


class Referral(Base):
    """Referral model - tracks user referrals."""

    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(String, ForeignKey("users.user_id"), nullable=False, comment="User who made the referral")
    referred_id = Column(String, nullable=False, unique=True, comment="User who was referred")
    created_at = Column(DateTime, default=datetime.utcnow, comment="When referral was made")
    notified = Column(Integer, default=0, comment="1 if referrer was notified")

    # Relationships
    referrer = relationship(
        "User",
        foreign_keys=[referrer_id],
        back_populates="referrals_made"
    )

    # Indexes
    __table_args__ = (
        Index("idx_referrals_referrer", "referrer_id"),
    )

    def __repr__(self):
        return f"<Referral(id={self.id}, referrer={self.referrer_id}, referred={self.referred_id})>"


def get_database_url() -> str:
    """Get database URL from config."""
    from app.config import settings
    return settings.database_url
