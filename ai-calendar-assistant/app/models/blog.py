"""Blog models for storing articles."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class BlogCategory(Base):
    """Blog category model."""

    __tablename__ = "blog_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    articles = relationship("BlogArticle", back_populates="category")


class BlogArticle(Base):
    """Blog article model."""

    __tablename__ = "blog_articles"

    id = Column(Integer, primary_key=True, index=True)

    # Article info
    title = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, nullable=False, index=True)

    # Content
    original_content = Column(Text, nullable=True)  # Оригинальный текст для справки
    rewritten_content = Column(Text, nullable=False)  # Рерайт для публикации
    summary = Column(Text, nullable=True)  # Краткое описание

    # Meta information
    category_id = Column(Integer, ForeignKey("blog_categories.id"), nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated tags

    # Images
    main_image_url = Column(String(1000), nullable=True)
    main_image_path = Column(String(500), nullable=True)  # Local path

    # Source tracking
    source_url = Column(String(1000), nullable=True)  # Откуда спарсили
    source_name = Column(String(100), nullable=True)  # Название источника
    source_published_at = Column(DateTime, nullable=True)  # Когда опубликовано в источнике

    # Publication
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)

    # SEO
    meta_title = Column(String(200), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("BlogCategory", back_populates="articles")


class BlogSource(Base):
    """Blog source configuration for parsers."""

    __tablename__ = "blog_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    url = Column(String(500), nullable=False)
    parser_type = Column(String(50), nullable=False)  # 'cian', 'generic', etc.
    is_active = Column(Boolean, default=True)

    # Parser configuration (JSON string)
    config = Column(Text, nullable=True)

    # Statistics
    last_parsed_at = Column(DateTime, nullable=True)
    total_articles_parsed = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlogDigest(Base):
    """Blog digest sent to users."""

    __tablename__ = "blog_digests"

    id = Column(Integer, primary_key=True, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Articles included in this digest (comma-separated IDs)
    article_ids = Column(String(500), nullable=False)

    # Statistics
    total_users_sent = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
