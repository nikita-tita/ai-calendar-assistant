"""Blog Pydantic schemas."""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class BlogCategoryBase(BaseModel):
    """Base blog category schema."""

    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None


class BlogCategoryCreate(BlogCategoryBase):
    """Schema for creating a blog category."""

    pass


class BlogCategory(BlogCategoryBase):
    """Blog category response schema."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BlogArticleBase(BaseModel):
    """Base blog article schema."""

    title: str = Field(..., max_length=500)
    slug: str = Field(..., max_length=500)
    summary: Optional[str] = None
    rewritten_content: str
    category_id: Optional[int] = None
    tags: Optional[str] = None
    main_image_url: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)


class BlogArticleCreate(BlogArticleBase):
    """Schema for creating a blog article."""

    original_content: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    source_published_at: Optional[datetime] = None


class BlogArticleUpdate(BaseModel):
    """Schema for updating a blog article."""

    title: Optional[str] = Field(None, max_length=500)
    slug: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = None
    rewritten_content: Optional[str] = None
    original_content: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[str] = None
    main_image_url: Optional[str] = None
    is_published: Optional[bool] = None
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)


class BlogArticle(BlogArticleBase):
    """Blog article response schema."""

    id: int
    original_content: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    source_published_at: Optional[datetime] = None
    is_published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    category: Optional[BlogCategory] = None

    class Config:
        from_attributes = True


class BlogArticleList(BaseModel):
    """Blog article list response schema."""

    total: int
    items: list[BlogArticle]


class ParsedArticle(BaseModel):
    """Schema for parsed article (before saving to DB)."""

    title: str
    content: str
    url: str
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None


class RewriteRequest(BaseModel):
    """Schema for article rewrite request."""

    original_content: str
    title: str
    preserve_structure: bool = True
    target_length: Optional[int] = None  # Target word count


class RewriteResponse(BaseModel):
    """Schema for article rewrite response."""

    rewritten_content: str
    summary: Optional[str] = None
    suggested_title: Optional[str] = None
    meta_description: Optional[str] = None


class BlogSourceBase(BaseModel):
    """Base blog source schema."""

    name: str = Field(..., max_length=100)
    url: str = Field(..., max_length=500)
    parser_type: str = Field(..., max_length=50)
    is_active: bool = True
    config: Optional[str] = None


class BlogSourceCreate(BlogSourceBase):
    """Schema for creating a blog source."""

    pass


class BlogSource(BlogSourceBase):
    """Blog source response schema."""

    id: int
    last_parsed_at: Optional[datetime] = None
    total_articles_parsed: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
