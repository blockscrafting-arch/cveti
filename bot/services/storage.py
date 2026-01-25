"""
Сервис для работы с Supabase Storage через нативный клиент Supabase (вместо S3)
"""
import logging
import json
from datetime import datetime
from bot.config import settings
from bot.services.supabase_client import supabase
from typing import Optional

logger = logging.getLogger(__name__)
LOG_PATH = r"d:\vladexecute\proj\CVETI\.cursor\debug.log"

class StorageService:
    """Сервис для загрузки файлов в Supabase Storage"""
    
    def __init__(self):
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.public_url_base = settings.SUPABASE_URL.rstrip('/')
        
        if not self.bucket:
            logger.warning("SUPABASE_STORAGE_BUCKET not set, uploads may fail")
    
    def _get_public_url(self, path: str) -> str:
        """Получить публичный URL для файла"""
        # Используем метод get_public_url из клиента, если возможно, или формируем вручную
        try:
            return supabase.storage.from_(self.bucket).get_public_url(path)
        except:
            return f"{self.public_url_base}/storage/v1/object/public/{self.bucket}/{path}"
    
    def _generate_file_path(self, filename: str, folder: str = "images") -> str:
        """Генерирует уникальный путь для файла"""
        import uuid
        from datetime import datetime
        
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_id = str(uuid.uuid4())[:8]
        timestamp = int(datetime.now().timestamp())
        
        # Очищаем folder от лишних слешей
        folder = folder.strip('/')
        
        return f"{folder}/{timestamp}_{unique_id}.{ext}"

    async def upload_file(self, file_content: bytes, filename: str, folder: str = "images") -> Optional[str]:
        """
        Загружает файл в Supabase Storage
        
        Args:
            file_content: Содержимое файла в байтах
            filename: Имя файла
            folder: Папка для сохранения (по умолчанию "images")
            
        Returns:
            Публичный URL загруженного файла или None при ошибке
        """
        try:
            # #region agent log
            try:
                payload = {
                    "location": "storage.py:55",
                    "message": "Upload start",
                    "data": {
                        "filename": filename,
                        "folder": folder,
                        "byte_len": len(file_content) if file_content else 0,
                        "bucket": self.bucket,
                        "supabase_type": type(supabase).__name__,
                        "has_storage_attr": hasattr(supabase, "storage")
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                }
                with open(LOG_PATH, 'a', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False)
                    f.write('\n')
                logger.info(f"DEBUG_LOG {json.dumps(payload, ensure_ascii=False)}")
            except Exception:
                pass
            # #endregion
            file_path = self._generate_file_path(filename, folder)
            
            # Загружаем через нативный клиент Supabase
            # Метод upload синхронный в текущей версии supabase-py, но выполняется быстро
            # При необходимости можно обернуть в run_in_executor, но для небольших файлов ок
            try:
                res = supabase.storage.from_(self.bucket).upload(
                    path=file_path,
                    file=file_content,
                    file_options={"content-type": self._get_content_type(filename), "upsert": "true"}
                )
                
                # Проверяем ответ (в разных версиях может быть разным)
                if hasattr(res, 'error') and res.error:
                    raise Exception(str(res.error))
                    
            except Exception as upload_error:
                error_str = str(upload_error)
                # Если бакета нет - пробуем создать (хотя лучше это делать через миграции)
                if "Bucket not found" in error_str or "The resource was not found" in error_str:
                    logger.error(f"Bucket '{self.bucket}' not found. Please run the SQL creation script.")
                raise upload_error

            public_url = self._get_public_url(file_path)
            # #region agent log
            try:
                payload = {
                    "location": "storage.py:83",
                    "message": "Upload finished",
                    "data": {
                        "file_path": file_path,
                        "public_url_set": bool(public_url)
                    },
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                }
                with open(LOG_PATH, 'a', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False)
                    f.write('\n')
                logger.info(f"DEBUG_LOG {json.dumps(payload, ensure_ascii=False)}")
            except Exception:
                pass
            # #endregion
            logger.info(f"File uploaded successfully: {file_path}")
            return public_url
                
        except Exception as e:
            logger.error(f"Error uploading file to Supabase Storage: {e}", exc_info=True)
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """Определяет Content-Type по расширению файла"""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'svg': 'image/svg+xml',
            'pdf': 'application/pdf'
        }
        
        return content_types.get(ext, 'application/octet-stream')
    
    async def delete_file(self, file_path: str) -> bool:
        """Удаляет файл из Supabase Storage"""
        try:
            supabase.storage.from_(self.bucket).remove([file_path])
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}", exc_info=True)
            return False
    
    def extract_path_from_url(self, url: str) -> Optional[str]:
        """Извлекает путь к файлу из публичного URL"""
        try:
            # Пытаемся найти часть после имени бакета
            if self.bucket in url:
                parts = url.split(f"/{self.bucket}/")
                if len(parts) > 1:
                    return parts[1]
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
