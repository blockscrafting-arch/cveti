"""
Общий Dispatcher для бота.
Используется как для polling (локальная разработка), так и для webhook (продакшен).
"""
from aiogram import Dispatcher
from bot.handlers import start, profile, book, info

# Создаем глобальный Dispatcher
dp = Dispatcher()

# Регистрация роутеров (обработчиков)
# ВАЖНО: profile.router должен быть ПЕРЕД start.router, 
# чтобы обработчик контакта срабатывал до команды /start
dp.include_router(profile.router)
dp.include_router(book.router)
dp.include_router(info.router)  # Информационные разделы (контакты, услуги, бонусы, поддержка)
dp.include_router(start.router)  # /start в конце, чтобы не перехватывать другие сообщения
