# КРИТИЧНО: Применяем патчи для Python 3.14 ДО импорта aiogram
import bot.patches  # noqa: F401

import asyncio
import logging
from aiogram import Bot
from bot.config import settings
from bot.dispatcher import dp

async def main():
    """
    Локальный запуск бота через polling.
    Используется только для разработки. В продакшене бот работает через webhook.
    """
    logging.basicConfig(level=logging.INFO)
    
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Запуск бота через polling (только для локальной разработки)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
