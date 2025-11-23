"""Blog article parsers."""

import re
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import structlog

from app.schemas.blog import ParsedArticle

logger = structlog.get_logger()


class BaseParser(ABC):
    """Base class for article parsers."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    @abstractmethod
    async def parse_article_list(self, url: str, limit: int = 10) -> List[str]:
        """Parse article list page and return article URLs.

        Args:
            url: URL of the article list page
            limit: Maximum number of articles to return

        Returns:
            List of article URLs
        """
        pass

    @abstractmethod
    async def parse_article(self, url: str) -> ParsedArticle:
        """Parse a single article.

        Args:
            url: URL of the article

        Returns:
            ParsedArticle object
        """
        pass

    async def fetch_page(self, url: str, timeout: int = 30) -> str:
        """Fetch a web page with proper headers.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            HTML content of the page
        """
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text

    def clean_html(self, html: str) -> str:
        """Clean HTML content, preserving paragraphs and structure.

        Args:
            html: HTML content

        Returns:
            Cleaned HTML with preserved structure
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style tags
        for tag in soup(['script', 'style', 'iframe', 'nav', 'footer', 'aside']):
            tag.decompose()

        # Remove comments
        for comment in soup.findAll(text=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()

        return str(soup)

    def html_to_structured_text(self, html: str) -> str:
        """Convert HTML to structured text with preserved formatting.

        Args:
            html: HTML content

        Returns:
            Structured text with headings and paragraphs
        """
        soup = BeautifulSoup(html, 'html.parser')

        result = []

        # Process all content tags
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'blockquote']):
            text = tag.get_text(strip=True)
            if not text:
                continue

            if tag.name.startswith('h'):
                # Headings
                level = int(tag.name[1])
                result.append(f"\n{'#' * level} {text}\n")
            elif tag.name == 'p':
                # Paragraphs
                result.append(f"{text}\n")
            elif tag.name in ['ul', 'ol']:
                # Lists
                for li in tag.find_all('li'):
                    li_text = li.get_text(strip=True)
                    result.append(f"• {li_text}\n")
            elif tag.name == 'blockquote':
                # Quotes
                result.append(f"> {text}\n")

        return '\n'.join(result)


class CianParser(BaseParser):
    """Parser for Cian.ru magazine articles."""

    def __init__(self):
        super().__init__()
        self.base_url = "https://spb.cian.ru"

    async def parse_article_list(self, url: str = "https://spb.cian.ru/magazine/", limit: int = 10) -> List[str]:
        """Parse Cian magazine main page and extract article URLs.

        Args:
            url: Magazine main page URL
            limit: Maximum number of articles to return

        Returns:
            List of article URLs
        """
        try:
            logger.info("parsing_article_list", url=url, limit=limit)
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')

            article_urls = []

            # Find article links (adjust selectors based on actual HTML structure)
            # Common patterns for Cian magazine:
            # 1. Links in article cards
            # 2. Links with specific classes
            # 3. Links in main content area

            # Try multiple selectors
            selectors = [
                'a[href*="/magazine/"]',  # General magazine links
                'article a',  # Links inside article tags
                '.article-card a',  # Common class pattern
                '.magazine-card a',  # Another common pattern
            ]

            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if not href:
                        continue

                    # Make absolute URL
                    if href.startswith('/'):
                        href = self.base_url + href
                    elif not href.startswith('http'):
                        continue

                    # Filter only article URLs (not category pages, etc.)
                    if '/magazine/' in href and href not in article_urls:
                        # Skip category pages and pagination
                        if not any(skip in href for skip in ['?page=', '/category/', '/tag/']):
                            article_urls.append(href)

                    if len(article_urls) >= limit:
                        break

                if len(article_urls) >= limit:
                    break

            logger.info("parsed_article_list", count=len(article_urls), urls=article_urls[:5])
            return article_urls[:limit]

        except Exception as e:
            logger.error("parse_article_list_error", error=str(e), url=url)
            raise

    async def parse_article(self, url: str) -> ParsedArticle:
        """Parse a single Cian magazine article.

        Args:
            url: Article URL

        Returns:
            ParsedArticle object with extracted data
        """
        try:
            logger.info("parsing_article", url=url)
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')

            # Extract title
            title = None
            title_selectors = ['h1', 'meta[property="og:title"]', '.article-title', 'title']
            for selector in title_selectors:
                if selector.startswith('meta'):
                    tag = soup.select_one(selector)
                    if tag:
                        title = tag.get('content')
                else:
                    tag = soup.select_one(selector)
                    if tag:
                        title = tag.get_text(strip=True)
                if title:
                    break

            if not title:
                title = "Без заголовка"

            # Extract main image
            image_url = None
            image_selectors = [
                'meta[property="og:image"]',
                '.article-image img',
                'article img',
                '.content img',
            ]
            for selector in image_selectors:
                if selector.startswith('meta'):
                    tag = soup.select_one(selector)
                    if tag:
                        image_url = tag.get('content')
                else:
                    tag = soup.select_one(selector)
                    if tag:
                        image_url = tag.get('src')
                if image_url:
                    # Make absolute URL
                    if image_url.startswith('/'):
                        image_url = self.base_url + image_url
                    break

            # Extract content
            content_html = None
            content_selectors = [
                'article',
                '.article-content',
                '.content',
                'main',
                '[itemprop="articleBody"]',
            ]

            for selector in content_selectors:
                tag = soup.select_one(selector)
                if tag:
                    content_html = str(tag)
                    break

            if not content_html:
                # Fallback: get all paragraphs
                paragraphs = soup.find_all('p')
                content_html = ''.join(str(p) for p in paragraphs)

            # Convert to structured text
            content = self.html_to_structured_text(content_html)

            # Extract publish date
            published_at = None
            date_selectors = [
                'meta[property="article:published_time"]',
                'time[datetime]',
                '.article-date',
            ]
            for selector in date_selectors:
                tag = soup.select_one(selector)
                if tag:
                    date_str = None
                    if selector.startswith('meta'):
                        date_str = tag.get('content')
                    elif 'datetime' in selector:
                        date_str = tag.get('datetime')
                    else:
                        date_str = tag.get_text(strip=True)

                    if date_str:
                        try:
                            # Try to parse ISO format
                            published_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            break
                        except ValueError:
                            pass

            # Extract category from URL or breadcrumbs
            category = None
            breadcrumbs = soup.select('.breadcrumb a, nav a')
            if breadcrumbs:
                # Last breadcrumb is usually category
                category = breadcrumbs[-1].get_text(strip=True) if len(breadcrumbs) > 1 else None

            # Extract tags/keywords
            tags = []
            meta_keywords = soup.select_one('meta[name="keywords"]')
            if meta_keywords:
                keywords = meta_keywords.get('content', '')
                tags = [tag.strip() for tag in keywords.split(',') if tag.strip()]

            logger.info("parsed_article", url=url, title=title, content_length=len(content))

            return ParsedArticle(
                title=title,
                content=content,
                url=url,
                published_at=published_at,
                image_url=image_url,
                category=category,
                tags=tags if tags else None,
            )

        except Exception as e:
            logger.error("parse_article_error", error=str(e), url=url)
            raise


class GenericParser(BaseParser):
    """Generic parser for various websites (fallback)."""

    async def parse_article_list(self, url: str, limit: int = 10) -> List[str]:
        """Parse generic website and extract article URLs.

        This is a basic implementation that looks for common article patterns.
        """
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')

            article_urls = []
            links = soup.find_all('a', href=True)

            for link in links:
                href = link['href']

                # Make absolute URL
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)

                # Basic filtering: must be HTTP(S) link
                if href.startswith('http') and href not in article_urls:
                    article_urls.append(href)

                if len(article_urls) >= limit:
                    break

            return article_urls[:limit]

        except Exception as e:
            logger.error("generic_parse_error", error=str(e), url=url)
            return []

    async def parse_article(self, url: str) -> ParsedArticle:
        """Parse a generic article."""
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')

            # Get title
            title_tag = soup.find('h1') or soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else "Без заголовка"

            # Get main content
            article_tag = soup.find('article') or soup.find('main')
            if article_tag:
                content = self.html_to_structured_text(str(article_tag))
            else:
                # Fallback: all paragraphs
                paragraphs = soup.find_all('p')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            return ParsedArticle(
                title=title,
                content=content,
                url=url,
            )

        except Exception as e:
            logger.error("generic_parse_article_error", error=str(e), url=url)
            raise
