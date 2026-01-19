from aiogram import Bot
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

async def send_loyalty_notification(bot: Bot, tg_id: int, points: int):
    """
    Отправляет уведомление пользователю о начислении баллов.
    
    Args:
        bot: Экземпляр Bot (передается извне для переиспользования)
        tg_id: Telegram ID пользователя
        points: Количество начисленных баллов
    """
    try:
        text = (
            f"🎁 Вам начислено {points} баллов лояльности!\n"
            f"Спасибо, что выбираете нашу студию. ✨\n\n"
            f"Посмотреть новый баланс можно в вашем профиле."
        )
        await bot.send_message(tg_id, text)
        logger.info(f"Notification sent to {tg_id} for {points} points")
    except Exception as e:
        logger.error(f"Failed to send notification to {tg_id}: {e}", exc_info=True)

async def send_broadcast_message(bot: Bot, tg_id: int, message: str, image_url: Optional[str] = None) -> bool:
    """
    Отправляет сообщение рассылки пользователю.
    """
    try:
        if image_url:
            # Отправляем фото с подписью
            await bot.send_photo(tg_id, photo=image_url, caption=message)
            logger.info(f"Broadcast photo sent to {tg_id}")
        else:
            # Отправляем текстовое сообщение
            await bot.send_message(tg_id, message)
            logger.info(f"Broadcast message sent to {tg_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send broadcast to {tg_id}: {e}", exc_info=True)
        return False
