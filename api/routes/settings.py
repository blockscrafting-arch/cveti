from fastapi import APIRouter, Header, HTTPException, Depends
from bot.services.auth import validate_init_data, get_user_id_from_init_data
from bot.services.settings import get_setting, update_setting, get_all_settings, clear_cache
from bot.config import settings
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)


async def get_current_admin(x_tg_init_data: Optional[str] = Header(None)):
    """Проверяет, является ли пользователь администратором"""
    try:
        if not x_tg_init_data or not validate_init_data(x_tg_init_data):
            raise HTTPException(status_code=401, detail="Invalid initData")
            
        tg_id = get_user_id_from_init_data(x_tg_init_data)
        if not tg_id or tg_id not in settings.ADMIN_IDS:
            logger.warning(f"Unauthorized admin access attempt: tg_id={tg_id}")
            raise HTTPException(status_code=403, detail="Admin access denied")
        
        return tg_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_admin: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class SettingUpdate(BaseModel):
    value: Any = Field(..., description="Новое значение настройки")
    type: Optional[str] = Field(None, description="Тип значения (string, number, float, boolean)")


@router.get("")
async def get_settings(
    _: int = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Получает все настройки приложения (только для админов)
    """
    try:
        all_settings = await get_all_settings()
        return {
            "success": True,
            "settings": all_settings
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении настроек")


@router.put("/{key}")
async def update_setting_by_key(
    key: str,
    setting_update: SettingUpdate,
    _: int = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Обновляет настройку по ключу (только для админов)
    """
    try:
        # Определяем тип автоматически, если не указан
        setting_type = setting_update.type
        if not setting_type:
            if key in ("loyalty_percentage", "loyalty_max_spend_percentage"):
                setting_type = "float"
            elif key in ("loyalty_expiration_days", "welcome_bonus_amount"):
                setting_type = "number"
            else:
                setting_type = "string"
        
        # Валидация значений
        value = setting_update.value
        if key == "loyalty_percentage" or key == "loyalty_max_spend_percentage":
            value = float(value)
            if not (0 <= value <= 1):
                raise HTTPException(status_code=400, detail="Значение должно быть от 0 до 1")
        elif key == "loyalty_expiration_days" or key == "welcome_bonus_amount":
            value = int(value)
            if value < 0:
                raise HTTPException(status_code=400, detail="Значение не может быть отрицательным")
        
        success = await update_setting(key, value, setting_type)
        if not success:
            raise HTTPException(status_code=500, detail="Ошибка при обновлении настройки")
        
        clear_cache()
        return {
            "success": True,
            "key": key,
            "value": value,
            "message": "Настройка обновлена"
        }
    except Exception as e:
        logger.error(f"Error updating setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))
