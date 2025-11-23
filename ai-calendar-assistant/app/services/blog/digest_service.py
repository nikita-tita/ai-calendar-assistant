"""Blog digest service for daily article summaries."""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, not_
import structlog

from app.models.blog import BlogArticle, BlogDigest

logger = structlog.get_logger()


class BlogDigestService:
    """Service for creating and managing blog digests."""

    def __init__(self, db: Session):
        """Initialize digest service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_digest_articles(
        self,
        limit: int = 3,
        hours_back: int = 48,
        exclude_sent: bool = True
    ) -> List[BlogArticle]:
        """Get articles for digest.

        Args:
            limit: Maximum number of articles to return
            hours_back: How many hours back to look for articles
            exclude_sent: Exclude articles already sent in previous digests

        Returns:
            List of articles for digest
        """
        # Calculate time threshold
        threshold = datetime.utcnow() - timedelta(hours=hours_back)

        # Base query: published articles from last N hours
        query = self.db.query(BlogArticle).filter(
            and_(
                BlogArticle.is_published == True,
                BlogArticle.published_at >= threshold
            )
        )

        # Exclude articles already sent in digests
        if exclude_sent:
            # Get all article IDs that were already sent
            sent_digests = self.db.query(BlogDigest.article_ids).all()
            sent_article_ids = set()

            for digest in sent_digests:
                if digest.article_ids:
                    # Parse comma-separated IDs
                    ids = [int(id.strip()) for id in digest.article_ids.split(',') if id.strip()]
                    sent_article_ids.update(ids)

            if sent_article_ids:
                query = query.filter(not_(BlogArticle.id.in_(sent_article_ids)))

        # Order by publish date (newest first) and limit
        articles = query.order_by(BlogArticle.published_at.desc()).limit(limit).all()

        logger.info("digest_articles_selected",
                   count=len(articles),
                   hours_back=hours_back,
                   exclude_sent=exclude_sent)

        return articles

    def create_digest(self, article_ids: List[int], total_users_sent: int = 0) -> BlogDigest:
        """Create a new digest record.

        Args:
            article_ids: List of article IDs included in digest
            total_users_sent: Number of users the digest was sent to

        Returns:
            Created digest record
        """
        # Convert list of IDs to comma-separated string
        article_ids_str = ','.join(str(id) for id in article_ids)

        digest = BlogDigest(
            article_ids=article_ids_str,
            total_users_sent=total_users_sent,
            sent_at=datetime.utcnow()
        )

        self.db.add(digest)
        self.db.commit()
        self.db.refresh(digest)

        logger.info("digest_created",
                   digest_id=digest.id,
                   article_count=len(article_ids),
                   users_sent=total_users_sent)

        return digest

    def get_recent_digests(self, limit: int = 10) -> List[BlogDigest]:
        """Get recent digests.

        Args:
            limit: Maximum number of digests to return

        Returns:
            List of recent digests
        """
        return self.db.query(BlogDigest).order_by(
            BlogDigest.sent_at.desc()
        ).limit(limit).all()

    def was_article_sent(self, article_id: int) -> bool:
        """Check if article was already sent in a digest.

        Args:
            article_id: Article ID to check

        Returns:
            True if article was sent, False otherwise
        """
        digests = self.db.query(BlogDigest.article_ids).all()

        for digest in digests:
            if digest.article_ids:
                ids = [int(id.strip()) for id in digest.article_ids.split(',') if id.strip()]
                if article_id in ids:
                    return True

        return False

    def format_article_preview(self, article: BlogArticle, max_length: int = 200) -> str:
        """Format article preview for Telegram message.

        Args:
            article: Blog article
            max_length: Maximum length of preview text

        Returns:
            Formatted preview text
        """
        # Use summary if available, otherwise use first part of content
        preview = article.summary or article.rewritten_content

        # Remove markdown headings
        import re
        preview = re.sub(r'^#+\s+', '', preview, flags=re.MULTILINE)

        # Get first paragraph
        paragraphs = preview.split('\n\n')
        preview = paragraphs[0] if paragraphs else preview

        # Truncate if too long
        if len(preview) > max_length:
            preview = preview[:max_length].rsplit(' ', 1)[0] + '...'

        return preview.strip()
