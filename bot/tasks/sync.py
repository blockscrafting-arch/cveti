import asyncio
import logging
from bot.services.supabase_client import supabase
from bot.services.loyalty import sync_user_with_yclients
from bot.services.visits import sync_user_visits

logger = logging.getLogger(__name__)

# Ограничение батча за один проход (масштабируемость: не грузим 10k пользователей)
SYNC_BATCH_SIZE = 100
# Задержка между пользователями (снижает нагрузку на YClients API)
SYNC_DELAY_SECONDS = 1.0


async def run_periodic_sync():
    """
    Фоновая задача для периодической синхронизации пользователей с YClients.
    За один проход обрабатывается батч (SYNC_BATCH_SIZE). Запуск раз в 24 часа.
    """
    logger.info("Starting periodic YClients sync task (batch_size=%s)", SYNC_BATCH_SIZE)

    while True:
        try:
            users_res = (
                await supabase.table("users")
                .select("id")
                .eq("active", True)
                .limit(SYNC_BATCH_SIZE)
                .execute()
            )

            if users_res.data:
                logger.info("Syncing batch of %s users with YClients", len(users_res.data))
                for user in users_res.data:
                    user_id = user["id"]
                    try:
                        await sync_user_with_yclients(user_id)
                        await sync_user_visits(user_id, limit=50, force=True)
                    except Exception as e:
                        logger.error("Failed to sync user %s during periodic task: %s", user_id, e)
                    await asyncio.sleep(SYNC_DELAY_SECONDS)
                logger.info("Periodic sync batch completed")
            else:
                logger.info("No active users found for sync")

        except Exception as e:
            logger.error("Error in periodic sync task: %s", e, exc_info=True)

        await asyncio.sleep(86400)  # 24 часа
