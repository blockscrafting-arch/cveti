"""
Скрипт миграции изображений из внешних URL в Supabase Storage

Использование:
    python -m scripts.migrate_images [--dry-run] [--table TABLE]

Опции:
    --dry-run    Показать что будет сделано без реальных изменений
    --table      Мигрировать только указанную таблицу (services|masters|promotions)
"""
import asyncio
import sys
import os
import argparse
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from bot.services.storage import get_storage_service
from bot.services.supabase_client import supabase
from bot.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# HTTP клиент для скачивания изображений
http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)


def is_supabase_storage_url(url: str) -> bool:
    """Проверяет, является ли URL Supabase Storage URL"""
    if not url:
        return False
    supabase_prefix = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/"
    return url.startswith(supabase_prefix)


async def download_image(url: str) -> Optional[bytes]:
    """
    Скачивает изображение по URL
    
    Returns:
        Содержимое файла в байтах или None в случае ошибки
    """
    try:
        logger.info(f"Downloading image from {url}")
        response = await http_client.get(url)
        response.raise_for_status()
        
        # Проверяем, что это изображение
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            logger.warning(f"URL {url} is not an image (content-type: {content_type})")
            return None
        
        return response.content
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading {url}: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error downloading {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}", exc_info=True)
        return None


def get_filename_from_url(url: str) -> str:
    """Извлекает имя файла из URL"""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if not filename or '.' not in filename:
        # Если нет расширения, определяем по content-type или используем jpg
        return "image.jpg"
    return filename


async def migrate_service(service: Dict, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Мигрирует изображение услуги
    
    Returns:
        (success, message)
    """
    service_id = service['id']
    old_url = service.get('image_url')
    
    if not old_url or is_supabase_storage_url(old_url):
        return (True, f"Service {service_id}: already migrated or no image")
    
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate service {service_id}: {old_url}")
        return (True, f"Service {service_id}: would migrate")
    
    # Скачиваем изображение
    image_data = await download_image(old_url)
    if not image_data:
        return (False, f"Service {service_id}: failed to download image")
    
    # Загружаем в Supabase Storage
    filename = get_filename_from_url(old_url)
    storage_service = get_storage_service()
    new_url = await storage_service.upload_file(
        file_content=image_data,
        filename=filename,
        folder="services"
    )
    
    if not new_url:
        return (False, f"Service {service_id}: failed to upload to Storage")
    
    # Обновляем URL в БД
    try:
        await supabase.table("services").update({"image_url": new_url}).eq("id", service_id).execute()
        logger.info(f"Service {service_id}: migrated {old_url} -> {new_url}")
        return (True, f"Service {service_id}: migrated successfully")
    except Exception as e:
        logger.error(f"Service {service_id}: failed to update DB: {e}")
        return (False, f"Service {service_id}: failed to update DB")


async def migrate_master(master: Dict, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Мигрирует фото мастера
    
    Returns:
        (success, message)
    """
    master_id = master['id']
    old_url = master.get('photo_url')
    
    if not old_url or is_supabase_storage_url(old_url):
        return (True, f"Master {master_id}: already migrated or no photo")
    
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate master {master_id}: {old_url}")
        return (True, f"Master {master_id}: would migrate")
    
    # Скачиваем изображение
    image_data = await download_image(old_url)
    if not image_data:
        return (False, f"Master {master_id}: failed to download image")
    
    # Загружаем в Supabase Storage
    filename = get_filename_from_url(old_url)
    storage_service = get_storage_service()
    new_url = await storage_service.upload_file(
        file_content=image_data,
        filename=filename,
        folder="masters"
    )
    
    if not new_url:
        return (False, f"Master {master_id}: failed to upload to Storage")
    
    # Обновляем URL в БД
    try:
        await supabase.table("masters").update({"photo_url": new_url}).eq("id", master_id).execute()
        logger.info(f"Master {master_id}: migrated {old_url} -> {new_url}")
        return (True, f"Master {master_id}: migrated successfully")
    except Exception as e:
        logger.error(f"Master {master_id}: failed to update DB: {e}")
        return (False, f"Master {master_id}: failed to update DB")


async def migrate_promotion(promotion: Dict, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Мигрирует изображение акции
    
    Returns:
        (success, message)
    """
    promotion_id = promotion['id']
    old_url = promotion.get('image_url')
    
    if not old_url or is_supabase_storage_url(old_url):
        return (True, f"Promotion {promotion_id}: already migrated or no image")
    
    if dry_run:
        logger.info(f"[DRY-RUN] Would migrate promotion {promotion_id}: {old_url}")
        return (True, f"Promotion {promotion_id}: would migrate")
    
    # Скачиваем изображение
    image_data = await download_image(old_url)
    if not image_data:
        return (False, f"Promotion {promotion_id}: failed to download image")
    
    # Загружаем в Supabase Storage
    filename = get_filename_from_url(old_url)
    storage_service = get_storage_service()
    new_url = await storage_service.upload_file(
        file_content=image_data,
        filename=filename,
        folder="promotions"
    )
    
    if not new_url:
        return (False, f"Promotion {promotion_id}: failed to upload to Storage")
    
    # Обновляем URL в БД
    try:
        await supabase.table("promotions").update({"image_url": new_url}).eq("id", promotion_id).execute()
        logger.info(f"Promotion {promotion_id}: migrated {old_url} -> {new_url}")
        return (True, f"Promotion {promotion_id}: migrated successfully")
    except Exception as e:
        logger.error(f"Promotion {promotion_id}: failed to update DB: {e}")
        return (False, f"Promotion {promotion_id}: failed to update DB")


async def migrate_all(dry_run: bool = False, table: Optional[str] = None):
    """Выполняет миграцию всех изображений"""
    
    logger.info("=" * 60)
    logger.info("Image Migration Script")
    logger.info("=" * 60)
    
    # Проверка конфигурации
    if not settings.SUPABASE_URL:
        logger.error("SUPABASE_URL not configured!")
        sys.exit(1)
    
    if not settings.SUPABASE_STORAGE_S3_ENDPOINT:
        logger.error("SUPABASE_STORAGE_S3_ENDPOINT not configured!")
        sys.exit(1)
    
    if not settings.SUPABASE_STORAGE_ACCESS_KEY or not settings.SUPABASE_STORAGE_SECRET_KEY:
        logger.error("Supabase Storage credentials not configured!")
        sys.exit(1)
    
    if dry_run:
        logger.info("DRY-RUN MODE: No changes will be made")
    else:
        logger.warning("LIVE MODE: Changes will be made to the database!")
        logger.warning("Make sure you have a database backup!")
    
    logger.info("")
    
    # Статистика
    stats = {
        'services': {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0},
        'masters': {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0},
        'promotions': {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
    }
    
    # Миграция услуг
    if not table or table == 'services':
        logger.info("Migrating services...")
        try:
            services_res = await supabase.table("services").select("*").execute()
            services = services_res.data if services_res.data else []
            
            for service in services:
                stats['services']['total'] += 1
                success, message = await migrate_service(service, dry_run)
                
                if 'already migrated' in message or 'no image' in message:
                    stats['services']['skipped'] += 1
                elif success:
                    stats['services']['success'] += 1
                else:
                    stats['services']['failed'] += 1
                
                logger.info(f"  {message}")
        except Exception as e:
            logger.error(f"Error migrating services: {e}", exc_info=True)
    
    # Миграция мастеров
    if not table or table == 'masters':
        logger.info("Migrating masters...")
        try:
            masters_res = await supabase.table("masters").select("*").execute()
            masters = masters_res.data if masters_res.data else []
            
            for master in masters:
                stats['masters']['total'] += 1
                success, message = await migrate_master(master, dry_run)
                
                if 'already migrated' in message or 'no photo' in message:
                    stats['masters']['skipped'] += 1
                elif success:
                    stats['masters']['success'] += 1
                else:
                    stats['masters']['failed'] += 1
                
                logger.info(f"  {message}")
        except Exception as e:
            logger.error(f"Error migrating masters: {e}", exc_info=True)
    
    # Миграция акций
    if not table or table == 'promotions':
        logger.info("Migrating promotions...")
        try:
            promotions_res = await supabase.table("promotions").select("*").execute()
            promotions = promotions_res.data if promotions_res.data else []
            
            for promotion in promotions:
                stats['promotions']['total'] += 1
                success, message = await migrate_promotion(promotion, dry_run)
                
                if 'already migrated' in message or 'no image' in message:
                    stats['promotions']['skipped'] += 1
                elif success:
                    stats['promotions']['success'] += 1
                else:
                    stats['promotions']['failed'] += 1
                
                logger.info(f"  {message}")
        except Exception as e:
            logger.error(f"Error migrating promotions: {e}", exc_info=True)
    
    # Выводим статистику
    logger.info("")
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    
    for table_name, table_stats in stats.items():
        if table_stats['total'] > 0:
            logger.info(f"{table_name.capitalize()}:")
            logger.info(f"  Total: {table_stats['total']}")
            logger.info(f"  Success: {table_stats['success']}")
            logger.info(f"  Failed: {table_stats['failed']}")
            logger.info(f"  Skipped: {table_stats['skipped']}")
            logger.info("")
    
    total_success = sum(s['success'] for s in stats.values())
    total_failed = sum(s['failed'] for s in stats.values())
    total_skipped = sum(s['skipped'] for s in stats.values())
    
    logger.info(f"Overall: {total_success} migrated, {total_failed} failed, {total_skipped} skipped")
    logger.info("=" * 60)


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Migrate images from external URLs to Supabase Storage'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--table',
        choices=['services', 'masters', 'promotions'],
        help='Migrate only specified table'
    )
    
    args = parser.parse_args()
    
    try:
        await migrate_all(dry_run=args.dry_run, table=args.table)
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await http_client.aclose()


if __name__ == '__main__':
    asyncio.run(main())
