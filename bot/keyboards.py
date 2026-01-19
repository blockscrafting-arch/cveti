"""
Централизованное управление клавиатурами бота
"""
from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from bot.config import settings
from bot.services.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)


def get_registration_keyboard() -> types.ReplyKeyboardMarkup:
    """Клавиатура для регистрации (запрос номера телефона)"""
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(
        text="📱 Поделиться номером",
        request_contact=True
    ))
    return builder.as_markup(resize_keyboard=True)


async def get_main_menu(is_admin: bool = False) -> types.ReplyKeyboardMarkup:
    """Главное меню бота - загружается из БД"""
    builder = ReplyKeyboardBuilder()
    
    try:
        # Загружаем активные кнопки из БД
        query = supabase.table("bot_buttons").select("*").eq("is_active", True).order("row_number").order("order_in_row")
        
        # Если не админ, исключаем админские кнопки
        if not is_admin:
            query = query.eq("is_admin_only", False)
        
        res = await query.execute()
        buttons = res.data if res.data else []
        
        # Группируем кнопки по строкам
        rows = {}
        for button in buttons:
            row_num = button.get("row_number", 1)
            if row_num not in rows:
                rows[row_num] = []
            rows[row_num].append(button)
        
        # Создаем строки кнопок
        for row_num in sorted(rows.keys()):
            row_buttons = sorted(rows[row_num], key=lambda x: x.get("order_in_row", 0))
            keyboard_buttons = []
            
            for btn in row_buttons:
                button_text = btn.get("button_text", "")
                web_app_url = btn.get("web_app_url")
                
                if web_app_url and settings.BASE_URL.startswith("https://"):
                    # Кнопка с WebApp
                    keyboard_buttons.append(types.KeyboardButton(
                        text=button_text,
                        web_app=types.WebAppInfo(url=web_app_url)
                    ))
                elif not web_app_url and button_text == "📅 Записаться" and settings.BASE_URL.startswith("https://"):
                    # Специальная обработка для кнопки "Записаться" - добавляем WebApp если есть BASE_URL
                    keyboard_buttons.append(types.KeyboardButton(
                        text=button_text,
                        web_app=types.WebAppInfo(url=f"{settings.BASE_URL}/webapp")
                    ))
                else:
                    # Обычная кнопка
                    keyboard_buttons.append(types.KeyboardButton(text=button_text))
            
            if keyboard_buttons:
                builder.row(*keyboard_buttons)
        
        # Если нет кнопок в БД, используем дефолтные
        if not buttons:
            logger.warning("No buttons found in DB, using fallback")
            if settings.BASE_URL.startswith("https://"):
                builder.row(types.KeyboardButton(
                    text="📅 Записаться",
                    web_app=types.WebAppInfo(url=f"{settings.BASE_URL}/webapp")
                ))
            else:
                builder.row(types.KeyboardButton(text="📅 Записаться"))
            
            builder.row(
                types.KeyboardButton(text="👤 Мой профиль"),
                types.KeyboardButton(text="🌸 Наши услуги")
            )
            builder.row(
                types.KeyboardButton(text="🎁 Бонусы"),
                types.KeyboardButton(text="📍 Контакты")
            )
            builder.row(types.KeyboardButton(text="💬 Поддержка"))
            
            if is_admin:
                builder.row(types.KeyboardButton(text="⚙️ Админка"))
    
    except Exception as e:
        logger.error(f"Error loading buttons from DB: {e}", exc_info=True)
        # Fallback на дефолтные кнопки при ошибке
        if settings.BASE_URL.startswith("https://"):
            builder.row(types.KeyboardButton(
                text="📅 Записаться",
                web_app=types.WebAppInfo(url=f"{settings.BASE_URL}/webapp")
            ))
        else:
            builder.row(types.KeyboardButton(text="📅 Записаться"))
        
        builder.row(
            types.KeyboardButton(text="👤 Мой профиль"),
            types.KeyboardButton(text="🌸 Наши услуги")
        )
        builder.row(
            types.KeyboardButton(text="🎁 Бонусы"),
            types.KeyboardButton(text="📍 Контакты")
        )
        builder.row(types.KeyboardButton(text="💬 Поддержка"))
        
        if is_admin:
            builder.row(types.KeyboardButton(text="⚙️ Админка"))
    
    return builder.as_markup(resize_keyboard=True)


async def get_button_response(button_text: str) -> str:
    """Получить текст ответа для кнопки из БД"""
    try:
        res = await supabase.table("bot_buttons").select("response_text").eq("button_text", button_text).eq("is_active", True).single().execute()
        if res.data:
            return res.data.get("response_text", "")
    except Exception as e:
        logger.error(f"Error loading button response: {e}", exc_info=True)
    return ""


def get_profile_inline_keyboard() -> types.InlineKeyboardMarkup:
    """Inline клавиатура для профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(types.InlineKeyboardButton(
        text="📜 История баллов",
        callback_data="profile_history"
    ))
    
    if settings.BASE_URL.startswith("https://"):
        builder.row(types.InlineKeyboardButton(
            text="📱 Открыть Mini App",
            web_app=types.WebAppInfo(url=f"{settings.BASE_URL}/webapp")
        ))
    
    return builder.as_markup()


def get_contacts_inline_keyboard() -> types.InlineKeyboardMarkup:
    """Inline клавиатура для контактов"""
    builder = InlineKeyboardBuilder()
    
    # Здесь можно добавить реальные ссылки когда будут известны
    # builder.row(types.InlineKeyboardButton(
    #     text="📍 На карте",
    #     url="https://yandex.ru/maps/..."
    # ))
    
    # builder.row(types.InlineKeyboardButton(
    #     text="📸 Instagram",
    #     url="https://instagram.com/..."
    # ))
    
    return builder.as_markup()


def get_services_inline_keyboard() -> types.InlineKeyboardMarkup:
    """Inline клавиатура для услуг"""
    builder = InlineKeyboardBuilder()
    
    if settings.BASE_URL.startswith("https://"):
        builder.row(types.InlineKeyboardButton(
            text="📱 Открыть полный каталог",
            web_app=types.WebAppInfo(url=f"{settings.BASE_URL}/webapp")
        ))
    else:
        builder.row(types.InlineKeyboardButton(
            text="🌐 Записаться онлайн",
            url=settings.YCLIENTS_BOOKING_URL
        ))
    
    return builder.as_markup()


def get_support_inline_keyboard() -> types.InlineKeyboardMarkup:
    """Inline клавиатура для поддержки"""
    builder = InlineKeyboardBuilder()
    
    # Можно добавить ссылку на менеджера или чат
    # builder.row(types.InlineKeyboardButton(
    #     text="💬 Написать менеджеру",
    #     url="https://t.me/..."
    # ))
    
    return builder.as_markup()
