"""Blog service for CRUD operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import structlog
import os
import httpx
from pathlib import Path
import hashlib

from app.models.blog import BlogArticle, BlogCategory, BlogSource
from app.schemas.blog import (
    BlogArticleCreate,
    BlogArticleUpdate,
    BlogCategoryCreate,
    BlogSourceCreate,
    ParsedArticle
)
from app.services.blog.parser import CianParser, GenericParser, BaseParser
from app.services.blog.rewriter import YandexGPTRewriter

logger = structlog.get_logger()


class BlogService:
    """Service for managing blog articles."""

    def __init__(self, db: Session):
        """Initialize blog service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.rewriter = YandexGPTRewriter()
        self.parsers = {
            'cian': CianParser(),
            'generic': GenericParser(),
        }

    # Category CRUD

    def create_category(self, category: BlogCategoryCreate) -> BlogCategory:
        """Create a new blog category.

        Args:
            category: Category data

        Returns:
            Created category
        """
        db_category = BlogCategory(**category.model_dump())
        self.db.add(db_category)
        self.db.commit()
        self.db.refresh(db_category)

        logger.info("category_created", category_id=db_category.id, name=db_category.name)
        return db_category

    def get_category(self, category_id: int) -> Optional[BlogCategory]:
        """Get category by ID.

        Args:
            category_id: Category ID

        Returns:
            Category or None
        """
        return self.db.query(BlogCategory).filter(BlogCategory.id == category_id).first()

    def get_category_by_slug(self, slug: str) -> Optional[BlogCategory]:
        """Get category by slug.

        Args:
            slug: Category slug

        Returns:
            Category or None
        """
        return self.db.query(BlogCategory).filter(BlogCategory.slug == slug).first()

    def get_all_categories(self) -> List[BlogCategory]:
        """Get all categories.

        Returns:
            List of categories
        """
        return self.db.query(BlogCategory).all()

    # Article CRUD

    def create_article(self, article: BlogArticleCreate) -> BlogArticle:
        """Create a new blog article.

        Args:
            article: Article data

        Returns:
            Created article
        """
        db_article = BlogArticle(**article.model_dump())
        self.db.add(db_article)
        self.db.commit()
        self.db.refresh(db_article)

        logger.info("article_created", article_id=db_article.id, title=db_article.title)
        return db_article

    def get_article(self, article_id: int) -> Optional[BlogArticle]:
        """Get article by ID.

        Args:
            article_id: Article ID

        Returns:
            Article or None
        """
        return self.db.query(BlogArticle).filter(BlogArticle.id == article_id).first()

    def get_article_by_slug(self, slug: str) -> Optional[BlogArticle]:
        """Get article by slug.

        Args:
            slug: Article slug

        Returns:
            Article or None
        """
        return self.db.query(BlogArticle).filter(BlogArticle.slug == slug).first()

    def get_articles(
        self,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[int] = None,
        published_only: bool = True
    ) -> List[BlogArticle]:
        """Get list of articles with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            category_id: Filter by category ID
            published_only: Return only published articles

        Returns:
            List of articles
        """
        query = self.db.query(BlogArticle)

        if published_only:
            query = query.filter(BlogArticle.is_published == True)

        if category_id:
            query = query.filter(BlogArticle.category_id == category_id)

        query = query.order_by(BlogArticle.created_at.desc())
        return query.offset(skip).limit(limit).all()

    def update_article(self, article_id: int, article_update: BlogArticleUpdate) -> Optional[BlogArticle]:
        """Update article.

        Args:
            article_id: Article ID
            article_update: Article update data

        Returns:
            Updated article or None
        """
        db_article = self.get_article(article_id)
        if not db_article:
            return None

        update_data = article_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_article, field, value)

        db_article.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_article)

        logger.info("article_updated", article_id=article_id)
        return db_article

    def delete_article(self, article_id: int) -> bool:
        """Delete article.

        Args:
            article_id: Article ID

        Returns:
            True if deleted, False if not found
        """
        db_article = self.get_article(article_id)
        if not db_article:
            return False

        self.db.delete(db_article)
        self.db.commit()

        logger.info("article_deleted", article_id=article_id)
        return True

    def publish_article(self, article_id: int) -> Optional[BlogArticle]:
        """Publish article.

        Args:
            article_id: Article ID

        Returns:
            Published article or None
        """
        db_article = self.get_article(article_id)
        if not db_article:
            return None

        db_article.is_published = True
        db_article.published_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_article)

        logger.info("article_published", article_id=article_id)
        return db_article

    def unpublish_article(self, article_id: int) -> Optional[BlogArticle]:
        """Unpublish article.

        Args:
            article_id: Article ID

        Returns:
            Unpublished article or None
        """
        db_article = self.get_article(article_id)
        if not db_article:
            return None

        db_article.is_published = False
        self.db.commit()
        self.db.refresh(db_article)

        logger.info("article_unpublished", article_id=article_id)
        return db_article

    # Parsing and Rewriting

    async def parse_and_create_article(
        self,
        url: str,
        parser_type: str = 'cian',
        auto_rewrite: bool = True,
        auto_publish: bool = False,
        category_id: Optional[int] = None
    ) -> BlogArticle:
        """Parse article from URL, rewrite it, and save to database.

        Args:
            url: Article URL
            parser_type: Type of parser to use ('cian', 'generic')
            auto_rewrite: Automatically rewrite article using Yandex GPT
            auto_publish: Automatically publish article after creation
            category_id: Category ID to assign

        Returns:
            Created article
        """
        logger.info("parsing_article", url=url, parser_type=parser_type)

        # Get parser
        parser = self.parsers.get(parser_type)
        if not parser:
            raise ValueError(f"Unknown parser type: {parser_type}")

        # Parse article
        parsed = await parser.parse_article(url)

        # Check if article already exists
        existing = self.db.query(BlogArticle).filter(BlogArticle.source_url == url).first()
        if existing:
            logger.warning("article_already_exists", url=url, article_id=existing.id)
            return existing

        # Rewrite article if requested
        if auto_rewrite:
            logger.info("rewriting_article", title=parsed.title)
            rewrite_response = await self.rewriter.rewrite_article(
                original_content=parsed.content,
                title=parsed.title,
                preserve_structure=True
            )
            rewritten_content = rewrite_response.rewritten_content
            summary = rewrite_response.summary
            suggested_title = rewrite_response.suggested_title or parsed.title
            meta_description = rewrite_response.meta_description
        else:
            rewritten_content = parsed.content
            summary = None
            suggested_title = parsed.title
            meta_description = None

        # Generate slug
        slug = self._generate_slug(suggested_title)

        # Download image if available
        image_path = None
        if parsed.image_url:
            try:
                image_path = await self._download_image(parsed.image_url, slug)
            except Exception as e:
                logger.error("image_download_error", error=str(e), url=parsed.image_url)

        # Create article
        article_data = BlogArticleCreate(
            title=suggested_title,
            slug=slug,
            original_content=parsed.content,
            rewritten_content=rewritten_content,
            summary=summary,
            category_id=category_id,
            tags=','.join(parsed.tags) if parsed.tags else None,
            main_image_url=parsed.image_url,
            main_image_path=image_path,
            source_url=url,
            source_name=parser_type,
            source_published_at=parsed.published_at,
            meta_description=meta_description,
            meta_title=suggested_title[:200] if suggested_title else None,
        )

        db_article = self.create_article(article_data)

        # Auto-publish if requested
        if auto_publish:
            self.publish_article(db_article.id)

        logger.info("article_created_from_url",
                   article_id=db_article.id,
                   url=url,
                   auto_rewrite=auto_rewrite,
                   auto_publish=auto_publish)

        return db_article

    async def batch_parse_articles(
        self,
        source_url: str,
        parser_type: str = 'cian',
        limit: int = 10,
        auto_rewrite: bool = True,
        auto_publish: bool = False,
        category_id: Optional[int] = None
    ) -> List[BlogArticle]:
        """Parse multiple articles from a source.

        Args:
            source_url: Source URL (e.g., magazine main page)
            parser_type: Type of parser to use
            limit: Maximum number of articles to parse
            auto_rewrite: Automatically rewrite articles
            auto_publish: Automatically publish articles
            category_id: Category ID to assign

        Returns:
            List of created articles
        """
        logger.info("batch_parsing_articles",
                   source_url=source_url,
                   limit=limit,
                   parser_type=parser_type)

        # Get parser
        parser = self.parsers.get(parser_type)
        if not parser:
            raise ValueError(f"Unknown parser type: {parser_type}")

        # Parse article list
        article_urls = await parser.parse_article_list(source_url, limit=limit)
        logger.info("article_urls_found", count=len(article_urls))

        created_articles = []

        # Parse each article
        for url in article_urls:
            try:
                article = await self.parse_and_create_article(
                    url=url,
                    parser_type=parser_type,
                    auto_rewrite=auto_rewrite,
                    auto_publish=auto_publish,
                    category_id=category_id
                )
                created_articles.append(article)

            except Exception as e:
                logger.error("article_parse_error", url=url, error=str(e))
                continue

        logger.info("batch_parsing_completed",
                   total_urls=len(article_urls),
                   created=len(created_articles))

        return created_articles

    # Source CRUD

    def create_source(self, source: BlogSourceCreate) -> BlogSource:
        """Create a new blog source.

        Args:
            source: Source data

        Returns:
            Created source
        """
        db_source = BlogSource(**source.model_dump())
        self.db.add(db_source)
        self.db.commit()
        self.db.refresh(db_source)

        logger.info("source_created", source_id=db_source.id, name=db_source.name)
        return db_source

    def get_active_sources(self) -> List[BlogSource]:
        """Get all active sources.

        Returns:
            List of active sources
        """
        return self.db.query(BlogSource).filter(BlogSource.is_active == True).all()

    # Helper methods

    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title.

        Args:
            title: Article title

        Returns:
            URL slug
        """
        import re
        from transliterate import translit

        # Transliterate Russian to Latin
        try:
            slug = translit(title, 'ru', reversed=True)
        except:
            slug = title

        # Convert to lowercase
        slug = slug.lower()

        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while self.get_article_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    async def _download_image(self, image_url: str, slug: str) -> str:
        """Download image from URL and save locally.

        Args:
            image_url: Image URL
            slug: Article slug (used for filename)

        Returns:
            Local file path
        """
        # Create images directory
        images_dir = Path("static/blog/images")
        images_dir.mkdir(parents=True, exist_ok=True)

        # Get file extension
        ext = Path(image_url).suffix or '.jpg'

        # Generate filename
        filename = f"{slug}{ext}"
        filepath = images_dir / filename

        # Download image
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(image_url)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

        logger.info("image_downloaded", url=image_url, path=str(filepath))
        return str(filepath)

    def get_statistics(self) -> dict:
        """Get blog statistics.

        Returns:
            Dictionary with statistics
        """
        total_articles = self.db.query(func.count(BlogArticle.id)).scalar()
        published_articles = self.db.query(func.count(BlogArticle.id)).filter(
            BlogArticle.is_published == True
        ).scalar()
        total_categories = self.db.query(func.count(BlogCategory.id)).scalar()

        return {
            'total_articles': total_articles,
            'published_articles': published_articles,
            'draft_articles': total_articles - published_articles,
            'total_categories': total_categories,
        }
