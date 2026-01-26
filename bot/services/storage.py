"""
Сервис для работы с Supabase Storage через нативный клиент Supabase (вместо S3)
"""
import logging
import json
import time
import os
import re
import hashlib
from datetime import datetime
from urllib.parse import quote, urlparse
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.auth import SigV4Auth
from botocore.credentials import Credentials
from botocore.awsrequest import AWSRequest
import httpx
import aioboto3
from bot.config import settings
from bot.services.supabase_client import supabase
from typing import Optional

logger = logging.getLogger(__name__)

def _get_debug_paths() -> list[str]:
    if os.name == "nt":
        return [r"d:\vladexecute\proj\CVETI\.cursor\debug.log"]
    return ["/tmp/debug.log", "/app/.cursor/debug.log", "/app/debug.log"]

DEBUG_LOG_PATHS = _get_debug_paths()

def _debug_log(payload: dict):
    try:
        payload.setdefault("sessionId", "debug-session")
        payload.setdefault("runId", "run1")
        payload["timestamp"] = int(time.time() * 1000)
        line = json.dumps(payload, ensure_ascii=False)
        wrote = False
        for log_path in DEBUG_LOG_PATHS:
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                wrote = True
                break
            except Exception:
                continue
        if not wrote:
            print(f"[debug_log] {line}")
    except Exception:
        pass
class StorageService:
    """Сервис для загрузки файлов в Supabase Storage"""
    
    def __init__(self):
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.public_url_base = (
            settings.SUPABASE_STORAGE_PUBLIC_URL_BASE.strip() or settings.SUPABASE_URL
        ).rstrip('/')
        self.public_url_template = settings.STORAGE_PUBLIC_URL_TEMPLATE.strip()
        self.s3_endpoint = settings.SUPABASE_STORAGE_S3_ENDPOINT
        self.s3_region = settings.SUPABASE_STORAGE_S3_REGION
        self.s3_access_key = settings.SUPABASE_STORAGE_ACCESS_KEY
        self.s3_secret_key = settings.SUPABASE_STORAGE_SECRET_KEY
        
        if not self.bucket:
            logger.warning("SUPABASE_STORAGE_BUCKET not set, uploads may fail")
    
    def _get_public_url(self, path: str) -> str:
        """Получить публичный URL для файла"""
        if self.public_url_template:
            return self.public_url_template.format(bucket=self.bucket, path=path)
        # Если задан публичный base URL, используем его
        if settings.SUPABASE_STORAGE_PUBLIC_URL_BASE:
            return f"{self.public_url_base}/storage/v1/object/public/{self.bucket}/{path}"
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
            file_path = self._generate_file_path(filename, folder)
            public_url = self._get_public_url(file_path)
            content_type = self._get_content_type(filename)
            # Предпочитаем S3 API (aioboto3), если настроены креды
            async def _upload_via_supabase() -> None:
                if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                    raise Exception("Supabase storage not configured")
                storage_url = (
                    f"{settings.SUPABASE_URL.rstrip('/')}"
                    f"/storage/v1/object/{self.bucket}/{quote(file_path, safe='/')}"
                )
                headers = {
                    "Authorization": f"Bearer {settings.SUPABASE_KEY}",
                    "apikey": settings.SUPABASE_KEY,
                    "Content-Type": content_type,
                    "x-upsert": "true"
                }
                # region agent log
                _debug_log({
                    "hypothesisId": "H4",
                    "location": "bot/services/storage.py:upload_file.supabase_http_attempt",
                    "message": "supabase storage http upload attempt",
                    "data": {
                        "bucket": self.bucket,
                        "key": file_path
                    }
                })
                # endregion
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        storage_url,
                        headers=headers,
                        content=file_content
                    )
                # region agent log
                _debug_log({
                    "hypothesisId": "H4",
                    "location": "bot/services/storage.py:upload_file.supabase_http_response",
                    "message": "supabase storage http response",
                    "data": {
                        "status_code": response.status_code
                    }
                })
                # endregion
                if response.status_code >= 400:
                    raise Exception(f"Supabase storage upload failed: {response.status_code}")

            payload_sha256 = hashlib.sha256(file_content).hexdigest() if file_content else None
            # region agent log
            _debug_log({
                "hypothesisId": "H5",
                "location": "bot/services/storage.py:upload_file.payload_hash",
                "message": "payload sha256",
                "data": {
                    "content_length": len(file_content) if file_content else 0,
                    "payload_sha256": payload_sha256
                }
            })
            # endregion

            async def _upload_via_sigv4_http() -> None:
                if not self.s3_endpoint or not self.s3_access_key or not self.s3_secret_key:
                    raise Exception("S3 HTTP upload not configured")
                endpoint = self.s3_endpoint.rstrip("/")
                key_path = quote(file_path, safe="/")
                url = f"{endpoint}/{self.bucket}/{key_path}"
                host = urlparse(endpoint).netloc
                payload_hash = payload_sha256 or hashlib.sha256(file_content).hexdigest()
                amz_date = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                headers = {
                    "Host": host,
                    "Content-Type": content_type,
                    "Content-Length": str(len(file_content) if file_content else 0),
                    "x-amz-content-sha256": payload_hash,
                    "x-amz-date": amz_date
                }
                request = AWSRequest(method="PUT", url=url, data=file_content, headers=headers)
                SigV4Auth(
                    Credentials(self.s3_access_key, self.s3_secret_key),
                    "s3",
                    self.s3_region
                ).add_auth(request)
                signed_headers = dict(request.headers)
                # region agent log
                _debug_log({
                    "hypothesisId": "H6",
                    "location": "bot/services/storage.py:upload_file.sigv4_http_attempt",
                    "message": "sigv4 http put attempt",
                    "data": {
                        "endpoint": endpoint,
                        "region": self.s3_region,
                        "bucket": self.bucket,
                        "key": file_path,
                        "content_length": len(file_content) if file_content else 0
                    }
                })
                # endregion
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.put(
                        url,
                        headers=signed_headers,
                        content=file_content
                    )
                error_code = None
                if response.text:
                    match = re.search(r"<Code>([^<]+)</Code>", response.text)
                    if match:
                        error_code = match.group(1)
                # region agent log
                _debug_log({
                    "hypothesisId": "H6",
                    "location": "bot/services/storage.py:upload_file.sigv4_http_response",
                    "message": "sigv4 http response",
                    "data": {
                        "status_code": response.status_code,
                        "error_code": error_code
                    }
                })
                # endregion
                if response.status_code >= 400:
                    detail = f"S3 http upload failed: {response.status_code}"
                    if error_code:
                        detail = f"{detail} {error_code}"
                    raise Exception(detail)

            if self.s3_endpoint and self.s3_access_key and self.s3_secret_key:
                session = aioboto3.Session()
                attempts = [
                    {
                        "label": "signed",
                        "payload_signing_enabled": True,
                        "config": Config(
                            signature_version="s3v4",
                            s3={"addressing_style": "path"}
                        )
                    },
                    {
                        "label": "unsigned",
                        "payload_signing_enabled": False,
                        "config": Config(
                            signature_version="s3v4",
                            s3={"addressing_style": "path", "payload_signing_enabled": False}
                        )
                    }
                ]
                uploaded = False
                last_error = None
                last_error_code = None
                for attempt in attempts:
                    # region agent log
                    _debug_log({
                        "hypothesisId": "H3",
                        "location": "bot/services/storage.py:upload_file.s3_attempt",
                        "message": "s3 put_object attempt",
                        "data": {
                            "endpoint": self.s3_endpoint,
                            "region": self.s3_region,
                            "bucket": self.bucket,
                            "content_length": len(file_content) if file_content else 0,
                            "content_type": content_type,
                            "attempt": attempt["label"],
                            "payload_signing_enabled": attempt["payload_signing_enabled"]
                        }
                    })
                    # endregion
                    print(
                        "[s3_upload] "
                        f"attempt={attempt['label']} "
                        f"payload_signing={attempt['payload_signing_enabled']} "
                        f"endpoint={self.s3_endpoint} region={self.s3_region} "
                        f"bucket={self.bucket} bytes={len(file_content) if file_content else 0} "
                        f"type={content_type}"
                    )
                    try:
                        async with session.client(
                            "s3",
                            endpoint_url=self.s3_endpoint,
                            region_name=self.s3_region,
                            aws_access_key_id=self.s3_access_key,
                            aws_secret_access_key=self.s3_secret_key,
                            config=attempt["config"]
                        ) as s3:
                            def _log_s3_headers(event_name: str):
                                def _handler(request, **kwargs):
                                    try:
                                        headers = request.headers or {}
                                        # region agent log
                                        _debug_log({
                                            "hypothesisId": "H5",
                                            "location": "bot/services/storage.py:upload_file.s3_headers",
                                            "message": "s3 request headers",
                                            "data": {
                                                "attempt": attempt["label"],
                                                "event": event_name,
                                                "x_amz_content_sha256": headers.get("x-amz-content-sha256") or headers.get("X-Amz-Content-SHA256"),
                                                "x_amz_decoded_content_length": headers.get("x-amz-decoded-content-length") or headers.get("X-Amz-Decoded-Content-Length"),
                                                "content_length": headers.get("content-length") or headers.get("Content-Length"),
                                                "transfer_encoding": headers.get("transfer-encoding") or headers.get("Transfer-Encoding"),
                                                "content_encoding": headers.get("content-encoding") or headers.get("Content-Encoding"),
                                                "content_md5": headers.get("content-md5") or headers.get("Content-MD5"),
                                                "expect": headers.get("expect") or headers.get("Expect")
                                            }
                                        })
                                        # endregion
                                    except Exception:
                                        pass
                                return _handler

                            s3.meta.events.register(
                                "request-created.s3.PutObject",
                                _log_s3_headers("request-created")
                            )
                            s3.meta.events.register(
                                "before-sign.s3.PutObject",
                                _log_s3_headers("before-sign")
                            )
                            s3.meta.events.register(
                                "before-send.s3.PutObject",
                                _log_s3_headers("before-send")
                            )

                            def _log_s3_headers_compat(request, **kwargs):
                                try:
                                    headers = request.headers or {}
                                    # region agent log
                                    _debug_log({
                                        "hypothesisId": "H5",
                                        "location": "bot/services/storage.py:upload_file.s3_headers",
                                        "message": "s3 request headers",
                                        "data": {
                                            "attempt": attempt["label"],
                                            "event": "compat-before-send",
                                            "x_amz_content_sha256": headers.get("x-amz-content-sha256") or headers.get("X-Amz-Content-SHA256"),
                                            "x_amz_decoded_content_length": headers.get("x-amz-decoded-content-length") or headers.get("X-Amz-Decoded-Content-Length"),
                                            "content_length": headers.get("content-length") or headers.get("Content-Length"),
                                            "transfer_encoding": headers.get("transfer-encoding") or headers.get("Transfer-Encoding"),
                                            "content_encoding": headers.get("content-encoding") or headers.get("Content-Encoding"),
                                            "content_md5": headers.get("content-md5") or headers.get("Content-MD5"),
                                            "expect": headers.get("expect") or headers.get("Expect")
                                        }
                                    })
                                    # endregion
                                except Exception:
                                    pass
                            s3.meta.events.register("before-send.s3.PutObject", _log_s3_headers_compat)
                            await s3.put_object(
                                Bucket=self.bucket,
                                Key=file_path,
                                Body=file_content,
                                ContentType=content_type,
                                ContentLength=len(file_content) if file_content else 0
                            )
                        # region agent log
                        _debug_log({
                            "hypothesisId": "H3",
                            "location": "bot/services/storage.py:upload_file.s3_success",
                            "message": "s3 put_object ok",
                            "data": {
                                "bucket": self.bucket,
                                "key": file_path,
                                "public_url": public_url,
                                "attempt": attempt["label"]
                            }
                        })
                        # endregion
                        print(f"[s3_upload] ok attempt={attempt['label']} bucket={self.bucket} key={file_path}")
                        uploaded = True
                        break
                    except ClientError as err:
                        last_error = err
                        error_code = None
                        if err.response:
                            error_code = err.response.get("Error", {}).get("Code")
                        last_error_code = error_code
                        # region agent log
                        _debug_log({
                            "hypothesisId": "H3",
                            "location": "bot/services/storage.py:upload_file.s3_error",
                            "message": "s3 put_object error",
                            "data": {
                                "attempt": attempt["label"],
                                "payload_signing_enabled": attempt["payload_signing_enabled"],
                                "error_code": error_code,
                                "error_type": type(err).__name__
                            }
                        })
                        # endregion
                        print(
                            "[s3_upload] "
                            f"error attempt={attempt['label']} "
                            f"code={error_code} type={type(err).__name__} "
                            f"message={str(err)}"
                        )
                        if error_code != "XAmzContentSHA256Mismatch":
                            raise
                if not uploaded and last_error and last_error_code == "XAmzContentSHA256Mismatch":
                    try:
                        await _upload_via_sigv4_http()
                        # region agent log
                        _debug_log({
                            "hypothesisId": "H6",
                            "location": "bot/services/storage.py:upload_file.sigv4_http_success",
                            "message": "sigv4 http upload ok",
                            "data": {
                                "bucket": self.bucket,
                                "key": file_path,
                                "public_url": public_url
                            }
                        })
                        # endregion
                        uploaded = True
                    except Exception as http_error:
                        # region agent log
                        _debug_log({
                            "hypothesisId": "H6",
                            "location": "bot/services/storage.py:upload_file.sigv4_http_error",
                            "message": "sigv4 http upload error",
                            "data": {
                                "error_type": type(http_error).__name__
                            }
                        })
                        # endregion
                if not uploaded and last_error:
                    if last_error_code == "XAmzContentSHA256Mismatch" and not settings.S3_SUPABASE_FALLBACK_ENABLED:
                        # region agent log
                        _debug_log({
                            "hypothesisId": "H5",
                            "location": "bot/services/storage.py:upload_file.supabase_fallback_disabled",
                            "message": "supabase fallback disabled",
                            "data": {
                                "bucket": self.bucket,
                                "key": file_path
                            }
                        })
                        # endregion
                    if last_error_code == "XAmzContentSHA256Mismatch" and settings.S3_SUPABASE_FALLBACK_ENABLED:
                        # region agent log
                        _debug_log({
                            "hypothesisId": "H3",
                            "location": "bot/services/storage.py:upload_file.supabase_fallback",
                            "message": "s3 checksum mismatch, fallback to supabase",
                            "data": {
                                "bucket": self.bucket,
                                "key": file_path
                            }
                        })
                        # endregion
                        try:
                            await _upload_via_supabase()
                            # region agent log
                            _debug_log({
                                "hypothesisId": "H3",
                                "location": "bot/services/storage.py:upload_file.supabase_fallback_ok",
                                "message": "supabase fallback ok",
                                "data": {
                                    "bucket": self.bucket,
                                    "key": file_path,
                                    "public_url": public_url
                                }
                            })
                            # endregion
                            uploaded = True
                        except Exception as upload_error:
                            # region agent log
                            _debug_log({
                                "hypothesisId": "H3",
                                "location": "bot/services/storage.py:upload_file.supabase_fallback_error",
                                "message": "supabase fallback error",
                                "data": {
                                    "error_type": type(upload_error).__name__
                                }
                            })
                            # endregion
                            raise last_error
                if not uploaded and last_error:
                    raise last_error
            else:
                # Фоллбек на нативный клиент Supabase (если есть storage)
                try:
                    if not settings.S3_SUPABASE_FALLBACK_ENABLED:
                        raise Exception("Supabase storage fallback disabled")
                    await _upload_via_supabase()
                except Exception as upload_error:
                    # region agent log
                    _debug_log({
                        "hypothesisId": "H3",
                        "location": "bot/services/storage.py:upload_file.supabase_error",
                        "message": "supabase upload error",
                        "data": {
                            "error_type": type(upload_error).__name__
                        }
                    })
                    # endregion
                    error_str = str(upload_error)
                    if "Bucket not found" in error_str or "The resource was not found" in error_str:
                        logger.error(f"Bucket '{self.bucket}' not found. Please run the SQL creation script.")
                    raise upload_error

            logger.info(f"File uploaded successfully: {file_path}")
            return public_url
                
        except Exception as e:
            # region agent log
            _debug_log({
                "hypothesisId": "H3",
                "location": "bot/services/storage.py:upload_file.error",
                "message": "upload error",
                "data": {
                    "error_type": type(e).__name__
                }
            })
            # endregion
            print(f"[s3_upload] error type={type(e).__name__} message={str(e)}")
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
            'avif': 'image/avif',
            'heic': 'image/heic',
            'heif': 'image/heif',
            'svg': 'image/svg+xml',
            'pdf': 'application/pdf'
        }
        
        return content_types.get(ext, 'application/octet-stream')
    
    async def delete_file(self, file_path: str) -> bool:
        """Удаляет файл из Supabase Storage"""
        try:
            if self.s3_endpoint and self.s3_access_key and self.s3_secret_key:
                session = aioboto3.Session()
                async with session.client(
                    "s3",
                    endpoint_url=self.s3_endpoint,
                    region_name=self.s3_region,
                    aws_access_key_id=self.s3_access_key,
                    aws_secret_access_key=self.s3_secret_key
                ) as s3:
                    await s3.delete_object(Bucket=self.bucket, Key=file_path)
            else:
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
