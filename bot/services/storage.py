"""
Сервис для работы с Supabase Storage через S3 API
"""
import aioboto3
from bot.config import settings
from typing import Optional
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class StorageService:
    """Сервис для загрузки файлов в Supabase Storage через S3 API"""
    
    def __init__(self):
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.endpoint_url = settings.SUPABASE_STORAGE_S3_ENDPOINT
        self.region = settings.SUPABASE_STORAGE_S3_REGION
        self.access_key = settings.SUPABASE_STORAGE_ACCESS_KEY
        self.secret_key = settings.SUPABASE_STORAGE_SECRET_KEY
        self.public_url_base = settings.SUPABASE_URL.rstrip('/')
        
        # Валидация обязательных параметров
        if not self.endpoint_url:
            logger.warning("SUPABASE_STORAGE_S3_ENDPOINT not set, uploads may fail")
        if not self.access_key:
            logger.warning("SUPABASE_STORAGE_ACCESS_KEY not set, uploads may fail")
        if not self.secret_key:
            logger.warning("SUPABASE_STORAGE_SECRET_KEY not set, uploads may fail")
        if not self.bucket:
            logger.warning("SUPABASE_STORAGE_BUCKET not set, uploads may fail")
        
        # Создаем сессию aioboto3
        self.session = aioboto3.Session()
    
    def _get_public_url(self, path: str) -> str:
        """Получить публичный URL для файла"""
        return f"{self.public_url_base}/storage/v1/object/public/{self.bucket}/{path}"
    
    def _generate_file_path(self, filename: str, folder: str = "images") -> str:
        """Генерирует уникальный путь для файла"""
        # Получаем расширение файла
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        # Генерируем уникальное имя: folder/YYYY-MM-DD/uuid.ext
        date_str = datetime.now().strftime("%Y-%m-%d")
        unique_id = str(uuid.uuid4())
        return f"{folder}/{date_str}/{unique_id}.{ext}"
    
    def _get_content_type(self, filename: str) -> str:
        """Определяет Content-Type по расширению файла"""
        ext = filename.split('.')[-1].lower() if '.' in filename else 'jpg'
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'svg': 'image/svg+xml',
            'bmp': 'image/bmp',
        }
        return content_types.get(ext, 'image/jpeg')
    
    async def upload_file(self, file_content: bytes, filename: str, folder: str = "images") -> Optional[str]:
        """
        Загружает файл в Supabase Storage через S3 API
        
        Args:
            file_content: Содержимое файла в байтах
            filename: Оригинальное имя файла
            folder: Папка для хранения (по умолчанию "images")
        
        Returns:
            Публичный URL файла или None в случае ошибки
        """
        try:
            # Проверяем конфигурацию
            if not self.endpoint_url or not self.access_key or not self.secret_key or not self.bucket:
                logger.error("Storage configuration incomplete. Check SUPABASE_STORAGE_* environment variables.")
                return None
            
            # Генерируем путь для файла
            file_path = self._generate_file_path(filename, folder)
            
            # Определяем Content-Type
            content_type = self._get_content_type(filename)
            
            # Загружаем через S3 API
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            ) as s3:
                try:
                    await s3.put_object(
                        Bucket=self.bucket,
                        Key=file_path,
                        Body=file_content,
                        ContentType=content_type
                        # ACL не нужен, так как bucket уже публичный
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "NoSuchBucket" in error_msg or "Bucket not found" in error_msg:
                        logger.error(f"Storage bucket '{self.bucket}' does not exist in Supabase Storage. Please create it in Supabase Dashboard: Storage -> Create bucket -> Name: '{self.bucket}' -> Public bucket")
                        raise Exception(f"Storage bucket '{self.bucket}' not found. Please create it in Supabase Dashboard.")
                    raise
            
            public_url = self._get_public_url(file_path)
            logger.info(f"File uploaded successfully via S3: {file_path}")
            return public_url
                
        except Exception as e:
            logger.error(f"Error uploading file to Supabase Storage via S3: {e}", exc_info=True)
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Удаляет файл из Supabase Storage через S3 API
        
        Args:
            file_path: Путь к файлу (относительно bucket)
        
        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            # Проверяем конфигурацию
            if not self.endpoint_url or not self.access_key or not self.secret_key or not self.bucket:
                logger.error("Storage configuration incomplete. Check SUPABASE_STORAGE_* environment variables.")
                return False
            
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            ) as s3:
                await s3.delete_object(
                    Bucket=self.bucket,
                    Key=file_path
                )
            
            logger.info(f"File deleted successfully via S3: {file_path}")
            return True
                
        except Exception as e:
            logger.error(f"Error deleting file from Supabase Storage via S3: {e}", exc_info=True)
            return False
    
    def extract_path_from_url(self, url: str) -> Optional[str]:
        """
        Извлекает путь к файлу из публичного URL
        
        Args:
            url: Публичный URL файла
        
        Returns:
            Путь к файлу или None
        """
        try:
            # Формат URL: {SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}
            prefix = f"{self.public_url_base}/storage/v1/object/public/{self.bucket}/"
            if url.startswith(prefix):
                return url[len(prefix):]
            return None
        except Exception:
            return None

# Глобальный экземпляр сервиса
_storage_service: Optional[StorageService] = None

def get_storage_service() -> StorageService:
    """Получить глобальный экземпляр StorageService"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
