import asyncio
import logging
from bot.services.supabase_client import supabase
from bot.services.loyalty import sync_user_with_yclients

logger = logging.getLogger(__name__)

async def run_periodic_sync():
    """
    Фоновая задача для периодической синхронизации всех пользователей с YClients.
    Запускается раз в 24 часа.
    """
    logger.info("Starting periodic YClients sync task")
    
    while True:
        try:
            # 1. Получаем всех пользователей, у которых есть yclients_id или телефон
            # Ограничиваем выборку активными пользователями
            users_res = await supabase.table("users")\
                .select("id")\
                .eq("active", True)\
                .execute()
            
            if users_res.data:
                logger.info(f"Syncing {len(users_res.data)} users with YClients")
                
                for user in users_res.data:
                    user_id = user["id"]
                    try:
                        # Синхронизируем каждого пользователя
                        # Добавляем небольшую задержку между запросами, чтобы не спамить API
                        await sync_user_with_yclients(user_id)
                        await asyncio.sleep(0.5) 
                    except Exception as e:
                        logger.error(f"Failed to sync user {user_id} during periodic task: {e}")
                
                logger.info("Periodic sync completed")
            else:
                logger.info("No active users found for sync")

        except Exception as e:
            logger.error(f"Error in periodic sync task: {e}", exc_info=True)
        
        # Ждем 24 часа перед следующим запуском
        # 24 * 60 * 60 = 86400 секунд
        await asyncio.sleep(86400)
