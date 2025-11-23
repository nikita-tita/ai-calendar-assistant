#!/usr/bin/env python3
"""CLI tool for parsing and publishing blog articles."""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import structlog

from app.config import settings
from app.models.blog import Base
from app.services.blog import BlogService
from app.schemas.blog import BlogCategoryCreate

logger = structlog.get_logger()


def setup_database():
    """Setup database and create tables."""
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


async def parse_single_article(args):
    """Parse a single article from URL."""
    db = setup_database()
    service = BlogService(db)

    print(f"📄 Парсинг статьи: {args.url}")

    try:
        article = await service.parse_and_create_article(
            url=args.url,
            parser_type=args.parser,
            auto_rewrite=not args.no_rewrite,
            auto_publish=args.publish,
            category_id=args.category_id
        )

        print(f"✅ Статья создана!")
        print(f"   ID: {article.id}")
        print(f"   Заголовок: {article.title}")
        print(f"   Slug: {article.slug}")
        print(f"   Опубликована: {'Да' if article.is_published else 'Нет'}")

        if article.source_url:
            print(f"   Источник: {article.source_url}")

        return article

    except Exception as e:
        print(f"❌ Ошибка при парсинге: {str(e)}")
        logger.error("parse_single_error", error=str(e), url=args.url)
        return None
    finally:
        db.close()


async def parse_batch_articles(args):
    """Parse multiple articles from a source."""
    db = setup_database()
    service = BlogService(db)

    print(f"📚 Пакетный парсинг из: {args.source_url}")
    print(f"   Лимит: {args.limit} статей")
    print(f"   Рерайт: {'Да' if not args.no_rewrite else 'Нет'}")
    print(f"   Автопубликация: {'Да' if args.publish else 'Нет'}")

    try:
        articles = await service.batch_parse_articles(
            source_url=args.source_url,
            parser_type=args.parser,
            limit=args.limit,
            auto_rewrite=not args.no_rewrite,
            auto_publish=args.publish,
            category_id=args.category_id
        )

        print(f"\n✅ Создано {len(articles)} статей:")
        for i, article in enumerate(articles, 1):
            status = "📗" if article.is_published else "📕"
            print(f"{i}. {status} {article.title[:60]}...")

        return articles

    except Exception as e:
        print(f"❌ Ошибка при пакетном парсинге: {str(e)}")
        logger.error("parse_batch_error", error=str(e), source_url=args.source_url)
        return []
    finally:
        db.close()


def list_articles(args):
    """List all articles."""
    db = setup_database()
    service = BlogService(db)

    try:
        articles = service.get_articles(
            skip=args.skip,
            limit=args.limit,
            published_only=not args.all
        )

        print(f"\n📚 Статьи ({len(articles)}):")
        for i, article in enumerate(articles, args.skip + 1):
            status = "📗" if article.is_published else "📕"
            print(f"{i}. {status} [{article.id}] {article.title}")
            print(f"   Slug: {article.slug}")
            print(f"   Создано: {article.created_at.strftime('%Y-%m-%d %H:%M')}")

    finally:
        db.close()


def publish_article(args):
    """Publish an article."""
    db = setup_database()
    service = BlogService(db)

    try:
        article = service.publish_article(args.article_id)
        if article:
            print(f"✅ Статья опубликована: {article.title}")
        else:
            print(f"❌ Статья с ID {args.article_id} не найдена")

    finally:
        db.close()


def unpublish_article(args):
    """Unpublish an article."""
    db = setup_database()
    service = BlogService(db)

    try:
        article = service.unpublish_article(args.article_id)
        if article:
            print(f"✅ Статья снята с публикации: {article.title}")
        else:
            print(f"❌ Статья с ID {args.article_id} не найдена")

    finally:
        db.close()


def create_category(args):
    """Create a new category."""
    db = setup_database()
    service = BlogService(db)

    try:
        category_data = BlogCategoryCreate(
            name=args.name,
            slug=args.slug,
            description=args.description
        )
        category = service.create_category(category_data)
        print(f"✅ Категория создана:")
        print(f"   ID: {category.id}")
        print(f"   Название: {category.name}")
        print(f"   Slug: {category.slug}")

    finally:
        db.close()


def list_categories(args):
    """List all categories."""
    db = setup_database()
    service = BlogService(db)

    try:
        categories = service.get_all_categories()
        print(f"\n📁 Категории ({len(categories)}):")
        for cat in categories:
            print(f"  [{cat.id}] {cat.name} ({cat.slug})")
            if cat.description:
                print(f"      {cat.description}")

    finally:
        db.close()


def show_statistics(args):
    """Show blog statistics."""
    db = setup_database()
    service = BlogService(db)

    try:
        stats = service.get_statistics()
        print("\n📊 Статистика блога:")
        print(f"   Всего статей: {stats['total_articles']}")
        print(f"   Опубликовано: {stats['published_articles']}")
        print(f"   Черновики: {stats['draft_articles']}")
        print(f"   Категорий: {stats['total_categories']}")

    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Парсер и менеджер статей для блога"
    )

    subparsers = parser.add_subparsers(dest='command', help='Команды')

    # Parse single article
    parse_parser = subparsers.add_parser('parse', help='Спарсить одну статью')
    parse_parser.add_argument('url', help='URL статьи')
    parse_parser.add_argument('--parser', default='cian', choices=['cian', 'generic'],
                            help='Тип парсера (по умолчанию: cian)')
    parse_parser.add_argument('--no-rewrite', action='store_true',
                            help='Не использовать рерайт через Yandex GPT')
    parse_parser.add_argument('--publish', action='store_true',
                            help='Автоматически опубликовать статью')
    parse_parser.add_argument('--category-id', type=int,
                            help='ID категории для статьи')

    # Parse batch
    batch_parser = subparsers.add_parser('batch', help='Пакетный парсинг статей')
    batch_parser.add_argument('source_url', help='URL источника (главная страница журнала)')
    batch_parser.add_argument('--limit', type=int, default=10,
                            help='Максимальное количество статей (по умолчанию: 10)')
    batch_parser.add_argument('--parser', default='cian', choices=['cian', 'generic'],
                            help='Тип парсера (по умолчанию: cian)')
    batch_parser.add_argument('--no-rewrite', action='store_true',
                            help='Не использовать рерайт через Yandex GPT')
    batch_parser.add_argument('--publish', action='store_true',
                            help='Автоматически публиковать статьи')
    batch_parser.add_argument('--category-id', type=int,
                            help='ID категории для всех статей')

    # List articles
    list_parser = subparsers.add_parser('list', help='Показать список статей')
    list_parser.add_argument('--skip', type=int, default=0,
                           help='Пропустить N статей')
    list_parser.add_argument('--limit', type=int, default=20,
                           help='Показать N статей')
    list_parser.add_argument('--all', action='store_true',
                           help='Показать все статьи (включая черновики)')

    # Publish article
    publish_parser = subparsers.add_parser('publish', help='Опубликовать статью')
    publish_parser.add_argument('article_id', type=int, help='ID статьи')

    # Unpublish article
    unpublish_parser = subparsers.add_parser('unpublish', help='Снять статью с публикации')
    unpublish_parser.add_argument('article_id', type=int, help='ID статьи')

    # Create category
    cat_create_parser = subparsers.add_parser('create-category', help='Создать категорию')
    cat_create_parser.add_argument('name', help='Название категории')
    cat_create_parser.add_argument('slug', help='URL slug категории')
    cat_create_parser.add_argument('--description', help='Описание категории')

    # List categories
    subparsers.add_parser('categories', help='Показать список категорий')

    # Statistics
    subparsers.add_parser('stats', help='Показать статистику')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Setup logging
    from app.utils.logger import setup_logging
    setup_logging(settings.log_level)

    # Execute command
    if args.command == 'parse':
        asyncio.run(parse_single_article(args))
    elif args.command == 'batch':
        asyncio.run(parse_batch_articles(args))
    elif args.command == 'list':
        list_articles(args)
    elif args.command == 'publish':
        publish_article(args)
    elif args.command == 'unpublish':
        unpublish_article(args)
    elif args.command == 'create-category':
        create_category(args)
    elif args.command == 'categories':
        list_categories(args)
    elif args.command == 'stats':
        show_statistics(args)


if __name__ == '__main__':
    main()
