"""Blog API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
import structlog

from app.schemas.blog import (
    BlogArticle,
    BlogArticleCreate,
    BlogArticleUpdate,
    BlogArticleList,
    BlogCategory,
    BlogCategoryCreate,
    BlogSource,
    BlogSourceCreate,
    RewriteRequest,
    RewriteResponse,
)
from app.services.blog import BlogService, YandexGPTRewriter
from app.models.blog import Base

logger = structlog.get_logger()

router = APIRouter(prefix="/blog", tags=["blog"])


# Database dependency
def get_db():
    """Get database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    # Create engine
    engine = create_engine(settings.database_url)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_blog_service(db: Session = Depends(get_db)) -> BlogService:
    """Get blog service instance."""
    return BlogService(db)


# Category endpoints

@router.post("/categories", response_model=BlogCategory)
async def create_category(
    category: BlogCategoryCreate,
    service: BlogService = Depends(get_blog_service)
):
    """Create a new blog category."""
    return service.create_category(category)


@router.get("/categories", response_model=List[BlogCategory])
async def list_categories(service: BlogService = Depends(get_blog_service)):
    """Get all blog categories."""
    return service.get_all_categories()


@router.get("/categories/{category_id}", response_model=BlogCategory)
async def get_category(
    category_id: int,
    service: BlogService = Depends(get_blog_service)
):
    """Get category by ID."""
    category = service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# Article endpoints

@router.post("/articles", response_model=BlogArticle)
async def create_article(
    article: BlogArticleCreate,
    service: BlogService = Depends(get_blog_service)
):
    """Create a new blog article."""
    return service.create_article(article)


@router.get("/articles", response_model=BlogArticleList)
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    published_only: bool = True,
    service: BlogService = Depends(get_blog_service)
):
    """Get list of articles with pagination."""
    from sqlalchemy import func
    from app.models.blog import BlogArticle as BlogArticleModel

    # Get total count
    query = service.db.query(func.count(BlogArticleModel.id))
    if published_only:
        query = query.filter(BlogArticleModel.is_published == True)
    if category_id:
        query = query.filter(BlogArticleModel.category_id == category_id)
    total = query.scalar()

    # Get articles
    articles = service.get_articles(
        skip=skip,
        limit=limit,
        category_id=category_id,
        published_only=published_only
    )

    return BlogArticleList(total=total, items=articles)


@router.get("/articles/{article_id}", response_model=BlogArticle)
async def get_article(
    article_id: int,
    service: BlogService = Depends(get_blog_service)
):
    """Get article by ID."""
    article = service.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/articles/slug/{slug}", response_model=BlogArticle)
async def get_article_by_slug(
    slug: str,
    service: BlogService = Depends(get_blog_service)
):
    """Get article by slug."""
    article = service.get_article_by_slug(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.patch("/articles/{article_id}", response_model=BlogArticle)
async def update_article(
    article_id: int,
    article_update: BlogArticleUpdate,
    service: BlogService = Depends(get_blog_service)
):
    """Update article."""
    article = service.update_article(article_id, article_update)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.delete("/articles/{article_id}")
async def delete_article(
    article_id: int,
    service: BlogService = Depends(get_blog_service)
):
    """Delete article."""
    success = service.delete_article(article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"message": "Article deleted successfully"}


@router.post("/articles/{article_id}/publish", response_model=BlogArticle)
async def publish_article(
    article_id: int,
    service: BlogService = Depends(get_blog_service)
):
    """Publish article."""
    article = service.publish_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/articles/{article_id}/unpublish", response_model=BlogArticle)
async def unpublish_article(
    article_id: int,
    service: BlogService = Depends(get_blog_service)
):
    """Unpublish article."""
    article = service.unpublish_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


# Parsing endpoints

@router.post("/parse/article", response_model=BlogArticle)
async def parse_article(
    url: str = Query(..., description="Article URL to parse"),
    parser_type: str = Query("cian", description="Parser type (cian, generic)"),
    auto_rewrite: bool = Query(True, description="Auto-rewrite using Yandex GPT"),
    auto_publish: bool = Query(False, description="Auto-publish after creation"),
    category_id: Optional[int] = Query(None, description="Category ID"),
    service: BlogService = Depends(get_blog_service)
):
    """Parse article from URL and create in database."""
    try:
        article = await service.parse_and_create_article(
            url=url,
            parser_type=parser_type,
            auto_rewrite=auto_rewrite,
            auto_publish=auto_publish,
            category_id=category_id
        )
        return article
    except Exception as e:
        logger.error("parse_article_endpoint_error", error=str(e), url=url)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse/batch", response_model=List[BlogArticle])
async def parse_batch_articles(
    background_tasks: BackgroundTasks,
    source_url: str = Query(..., description="Source URL (e.g., magazine main page)"),
    parser_type: str = Query("cian", description="Parser type"),
    limit: int = Query(10, ge=1, le=50, description="Max articles to parse"),
    auto_rewrite: bool = Query(True, description="Auto-rewrite articles"),
    auto_publish: bool = Query(False, description="Auto-publish articles"),
    category_id: Optional[int] = Query(None, description="Category ID"),
    service: BlogService = Depends(get_blog_service)
):
    """Parse multiple articles from a source (runs in background)."""
    try:
        # Run in background to avoid timeout
        articles = await service.batch_parse_articles(
            source_url=source_url,
            parser_type=parser_type,
            limit=limit,
            auto_rewrite=auto_rewrite,
            auto_publish=auto_publish,
            category_id=category_id
        )
        return articles
    except Exception as e:
        logger.error("batch_parse_error", error=str(e), source_url=source_url)
        raise HTTPException(status_code=500, detail=str(e))


# Rewriting endpoint

@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_article(request: RewriteRequest):
    """Rewrite article content using Yandex GPT."""
    try:
        rewriter = YandexGPTRewriter()
        response = await rewriter.rewrite_article(
            original_content=request.original_content,
            title=request.title,
            preserve_structure=request.preserve_structure,
            target_length=request.target_length
        )
        return response
    except Exception as e:
        logger.error("rewrite_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Source endpoints

@router.post("/sources", response_model=BlogSource)
async def create_source(
    source: BlogSourceCreate,
    service: BlogService = Depends(get_blog_service)
):
    """Create a new blog source."""
    return service.create_source(source)


@router.get("/sources", response_model=List[BlogSource])
async def list_sources(service: BlogService = Depends(get_blog_service)):
    """Get all active sources."""
    return service.get_active_sources()


# Statistics

@router.get("/statistics")
async def get_statistics(service: BlogService = Depends(get_blog_service)):
    """Get blog statistics."""
    return service.get_statistics()
