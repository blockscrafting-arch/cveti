# КРИТИЧНО: Применяем патчи для Python 3.14 ДО импорта pydantic
import bot.patches  # noqa: F401

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from typing import Union

# Загружаем .env.local в первую очередь, затем .env
load_dotenv('.env.local')
load_dotenv('.env')

class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Supabase Storage (S3 API)
    SUPABASE_STORAGE_S3_ENDPOINT: str = os.getenv("SUPABASE_STORAGE_S3_ENDPOINT", "")
    SUPABASE_STORAGE_S3_REGION: str = os.getenv("SUPABASE_STORAGE_S3_REGION", "eu-west-1")
    SUPABASE_STORAGE_ACCESS_KEY: str = os.getenv("SUPABASE_STORAGE_ACCESS_KEY", "")
    SUPABASE_STORAGE_SECRET_KEY: str = os.getenv("SUPABASE_STORAGE_SECRET_KEY", "")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "CVETi")
    
    # YClients
    YCLIENTS_PARTNER_TOKEN: str = os.getenv("YCLIENTS_PARTNER_TOKEN", "")  # Токен партнера (разработчика)
    YCLIENTS_USER_TOKEN: str = os.getenv("YCLIENTS_USER_TOKEN", "")  # User Token системного пользователя (создается при подключении интеграции)
    YCLIENTS_COMPANY_ID: str = os.getenv("YCLIENTS_COMPANY_ID", "443477")  # ID филиала/компании (НЕ партнера! Находится в URL: /company/443477 или в настройках приложения)
    YCLIENTS_BOOKING_URL: str = os.getenv("YCLIENTS_BOOKING_URL", "https://n12345.yclients.com/")  # Ссылка на онлайн-запись
    
    # Security
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "change_me_to_random_string") # Секрет для защиты вебхука
    ADMIN_IDS: Union[str, list[int]] = Field(default_factory=list)
    
    # App
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    # Loyalty
    LOYALTY_PERCENTAGE: float = float(os.getenv("LOYALTY_PERCENTAGE", "0.05"))  # 5% кэшбек по умолчанию
    LOYALTY_MAX_SPEND_PERCENTAGE: float = float(os.getenv("LOYALTY_MAX_SPEND_PERCENTAGE", "0.3"))  # Максимум 30% от чека можно оплатить баллами
    LOYALTY_EXPIRATION_DAYS: int = int(os.getenv("LOYALTY_EXPIRATION_DAYS", "90"))  # Баллы действуют 90 дней (3 месяца)
    
    @field_validator('ADMIN_IDS', mode='before')
    @classmethod
    def parse_admin_ids(cls, v: Union[str, list, int]) -> list[int]:
        """Парсит ADMIN_IDS из строки, списка или числа"""
        if isinstance(v, list):
            return [int(i) for i in v]
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            if not v.strip():
                return []
            # Парсим строку вида "123,456,789" или просто "123"
            return [int(i.strip()) for i in v.split(",") if i.strip()]
        return []
    
    def __init__(self, **kwargs):
        # Загружаем ADMIN_IDS из переменной окружения если не передано явно
        if 'ADMIN_IDS' not in kwargs:
            admin_ids_str = os.getenv("ADMIN_IDS", "")
            if admin_ids_str:
                kwargs['ADMIN_IDS'] = admin_ids_str
        super().__init__(**kwargs)
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
