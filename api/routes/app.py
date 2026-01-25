from fastapi import APIRouter, Header, HTTPException
from bot.services.auth import validate_init_data, get_user_id_from_init_data
from bot.services.supabase_client import supabase
from bot.services.loyalty import get_user_available_balance, sync_user_with_yclients
from bot.services.yclients_api import yclients
from bot.config import settings
from typing import Optional
import logging

router = APIRouter(prefix="/api/app", tags=["mini-app"])
logger = logging.getLogger(__name__)

@router.get("/profile")
async def get_app_profile(x_tg_init_data: Optional[str] = Header(None)):
    """Получает профиль пользователя для Mini App"""
    try:
        # 1. Валидация
        if not x_tg_init_data or not validate_init_data(x_tg_init_data):
            logger.warning("Invalid initData in profile request")
            raise HTTPException(status_code=401, detail="Invalid initData")
            
        tg_id = get_user_id_from_init_data(x_tg_init_data)
        if not tg_id:
            logger.warning("Could not extract tg_id from initData")
            raise HTTPException(status_code=401, detail="Invalid initData")
        
        # 2. Поиск в БД
        try:
            user_res = await supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        except Exception as e:
            logger.error(f"Database error in get_app_profile: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Database error")
        
        if not user_res.data:
            logger.info(f"User not found: tg_id={tg_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        user = user_res.data[0]
        
        # Синхронизируем баланс с YClients в приоритете
        try:
            sync_result = await sync_user_with_yclients(user["id"])
            if sync_result:
                user["balance"] = sync_result.get("balance", user.get("balance", 0))
            else:
                # Если синхронизация не удалась (например, не нашли в YClients), 
                # считаем по нашей базе как раньше
                available_balance = await get_user_available_balance(user["id"])
                user["balance"] = available_balance
        except Exception as e:
            logger.warning(f"Could not sync balance with YClients, using local calculation: {e}")
            try:
                available_balance = await get_user_available_balance(user["id"])
                user["balance"] = available_balance
            except Exception as inner_e:
                logger.error(f"Local balance calculation also failed: {inner_e}")
        
        # Проверяем, является ли пользователь администратором
        is_admin = tg_id in settings.ADMIN_IDS
        
        # 3. Получаем последние транзакции
        try:
            tx_res = await supabase.table("loyalty_transactions")\
                .select("*")\
                .eq("user_id", user["id"])\
                .order("created_at", desc=True)\
                .limit(10)\
                .execute()
        except Exception as e:
            logger.error(f"Database error fetching transactions: {e}", exc_info=True)
            # Возвращаем профиль без истории, если транзакции не загрузились
            tx_res = type('obj', (object,), {'data': []})()

        # 4. Получаем историю визитов из YClients
        visits = []
        try:
            yclients_id = user.get("yclients_id")
            if not yclients_id and user.get("phone"):
                client = await yclients.get_client_by_phone(user["phone"])
                if client and client.get("id"):
                    yclients_id = client["id"]
                    try:
                        await supabase.table("users").update({"yclients_id": yclients_id}).eq("id", user["id"]).execute()
                    except Exception as update_err:
                        logger.warning(f"Could not update yclients_id for user {user['id']}: {update_err}")

            if yclients_id:
                visits = await yclients.get_client_visits(yclients_id, limit=10)
        except Exception as e:
            logger.warning(f"Could not fetch visits from YClients: {e}")
        
        return {
            "user": user,
            "is_admin": is_admin,
            "history": tx_res.data if hasattr(tx_res, 'data') else [],
            "visits": visits
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_app_profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/content")
async def get_app_content():
    """Получает общий контент: услуги, мастера, акции"""
    try:
        # Сортируем по order, затем по id для стабильности
        services_res = await supabase.table("services").select("*").eq("is_active", True).order("order").order("id").execute()
        masters_res = await supabase.table("masters").select("*").order("order").order("id").execute()
        promotions_res = await supabase.table("promotions").select("*").eq("is_active", True).order("order").order("id").execute()
        
        return {
            "services": services_res.data if services_res.data else [],
            "masters": masters_res.data if masters_res.data else [],
            "promotions": promotions_res.data if promotions_res.data else [],
            "booking_url": settings.YCLIENTS_BOOKING_URL
        }
    except Exception as e:
        logger.error(f"Database error in get_app_content: {e}", exc_info=True)
        # Возвращаем пустые списки при ошибке БД
        return {
            "services": [],
            "masters": [],
            "promotions": [],
            "booking_url": settings.YCLIENTS_BOOKING_URL
        }
