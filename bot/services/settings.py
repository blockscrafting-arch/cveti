"""
Сервис для работы с настройками приложения из базы данных
Поддерживает кэширование для оптимизации производительности
"""
from bot.services.supabase_client import supabase
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Кэш настроек (обновляется каждые 5 минут)
_settings_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None
_cache_ttl = timedelta(minutes=5)


async def get_setting(key: str, default_value: Optional[Any] = None, use_cache: bool = True) -> Any:
    """
    Получает значение настройки по ключу
    
    Args:
        key: Ключ настройки
        default_value: Значение по умолчанию, если настройка не найдена
        use_cache: Использовать ли кэш (по умолчанию True)
    
    Returns:
        Значение настройки (строка, число, float или bool в зависимости от типа)
    """
    global _cache_timestamp, _settings_cache
    
    # Проверяем кэш
    if use_cache and _cache_timestamp and datetime.now() - _cache_timestamp < _cache_ttl:
        if key in _settings_cache:
            return _settings_cache[key]
    
    try:
        # Получаем настройку из БД
        result = await supabase.table("app_settings").select("*").eq("key", key).execute()
        
        if result.data and len(result.data) > 0:
            setting = result.data[0]
            value = setting["value"]
            setting_type = setting.get("type", "string")
            
            # Преобразуем значение в нужный тип
            converted_value = _convert_value(value, setting_type)
            
            # Обновляем кэш
            _settings_cache[key] = converted_value
            _cache_timestamp = datetime.now()
            
            return converted_value
        else:
            # Настройка не найдена, возвращаем дефолт
            if default_value is not None:
                return default_value
            logger.warning(f"Setting '{key}' not found and no default value provided")
            return None
            
    except Exception as e:
        logger.error(f"Error getting setting '{key}': {e}", exc_info=True)
        # При ошибке возвращаем дефолт или None
        return default_value


async def update_setting(key: str, value: Any, setting_type: str = "string") -> bool:
    """
    Обновляет или создает настройку
    
    Args:
        key: Ключ настройки
        value: Новое значение
        setting_type: Тип значения ('string', 'number', 'float', 'boolean')
    
    Returns:
        True если успешно, False при ошибке
    """
    try:
        # Преобразуем значение в строку для хранения
        value_str = str(value)
        
        # Используем RPC функцию для обновления
        result = await supabase.rpc("update_setting", {
            "p_key": key,
            "p_value": value_str,
            "p_type": setting_type
        }).execute()
        
        # Очищаем кэш для этой настройки
        if key in _settings_cache:
            del _settings_cache[key]
        
        logger.info(f"Setting '{key}' updated to '{value_str}'")
        return True
        
    except Exception as e:
        logger.error(f"Error updating setting '{key}': {e}", exc_info=True)
        return False


async def get_all_settings() -> Dict[str, Any]:
    """
    Получает все настройки из базы данных
    
    Returns:
        Словарь {ключ: значение} со всеми настройками
    """
    try:
        result = await supabase.table("app_settings").select("*").execute()
        
        settings_dict = {}
        if result.data:
            for setting in result.data:
                key = setting["key"]
                value = setting["value"]
                setting_type = setting.get("type", "string")
                settings_dict[key] = _convert_value(value, setting_type)
        
        return settings_dict
        
    except Exception as e:
        logger.error(f"Error getting all settings: {e}", exc_info=True)
        return {}


def clear_cache():
    """Очищает кэш настроек (полезно после обновления)"""
    global _settings_cache, _cache_timestamp
    _settings_cache = {}
    _cache_timestamp = None


def _convert_value(value: str, setting_type: str) -> Any:
    """
    Преобразует строковое значение в нужный тип
    
    Args:
        value: Строковое значение
        setting_type: Тип ('string', 'number', 'float', 'boolean')
    
    Returns:
        Преобразованное значение
    """
    if setting_type == "number":
        try:
            return int(value)
        except ValueError:
            return 0
    elif setting_type == "float":
        try:
            return float(value)
        except ValueError:
            return 0.0
    elif setting_type == "boolean":
        return value.lower() in ("true", "1", "yes", "on")
    else:
        return value
