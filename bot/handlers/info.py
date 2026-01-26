"""
Обработчики информационных разделов бота
"""
from aiogram import Router, types, F
from bot.keyboards import get_contacts_inline_keyboard, get_services_inline_keyboard, get_support_inline_keyboard, get_button_response
from bot.services.supabase_client import supabase
from bot.services.settings import get_setting
from bot.config import settings
import logging

router = Router()
logger = logging.getLogger(__name__)


async def send_button_response(message: types.Message, button_text: str, inline_keyboard=None):
    """Отправляет ответ для кнопки, используя текст из БД"""
    response_text = await get_button_response(button_text)
    
    if response_text:
        response_text = await _apply_placeholders(response_text)
        
        await message.answer(
            response_text,
            reply_markup=inline_keyboard,
            parse_mode="Markdown"
        )
    else:
        # Fallback на дефолтные ответы
        logger.warning(f"No response text found for button: {button_text}")
        await message.answer("❌ Информация временно недоступна.")


@router.message(F.text == "📍 Контакты")
async def show_contacts(message: types.Message):
    """Показывает контактную информацию студии"""
    await send_button_response(message, "📍 Контакты", get_contacts_inline_keyboard())


@router.message(F.text == "🎁 Бонусы")
async def show_bonuses(message: types.Message):
    """Показывает информацию о программе лояльности"""
    response_text = await get_button_response("🎁 Бонусы")
    
    if response_text:
        original_text = response_text
        response_text = await _apply_placeholders(response_text)
        if "Баллы действуют" not in original_text and "Можно оплатить" not in original_text:
            loyalty_max_spend_percentage = await get_setting('loyalty_max_spend_percentage', settings.LOYALTY_MAX_SPEND_PERCENTAGE)
            loyalty_expiration_days = await get_setting('loyalty_expiration_days', settings.LOYALTY_EXPIRATION_DAYS)
            response_text += (
                f"\n\n💳 Можно оплатить до {int(float(loyalty_max_spend_percentage) * 100)}% от суммы чека"
                f"\n⏰ Баллы действуют {int(loyalty_expiration_days)} дней"
            )
        await message.answer(response_text, parse_mode="Markdown")
    else:
        await message.answer("❌ Информация временно недоступна.")


@router.message(F.text == "🌸 Наши услуги")
async def show_services(message: types.Message):
    """Показывает информацию об услугах"""
    await send_button_response(message, "🌸 Наши услуги", get_services_inline_keyboard())


@router.message(F.text == "💬 Поддержка")
async def show_support(message: types.Message):
    """Показывает информацию о поддержке"""
    await send_button_response(message, "💬 Поддержка", get_support_inline_keyboard())


@router.message(F.text == "⚙️ Админка")
async def show_admin_info(message: types.Message):
    """Информация об админке (для админов)"""
    tg_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом
    if tg_id not in settings.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    response_text = await get_button_response("⚙️ Админка")
    
    if response_text:
        if settings.BASE_URL.startswith("https://"):
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(
                text="📱 Открыть админ-панель",
                web_app=types.WebAppInfo(url=f"{settings.BASE_URL}/webapp")
            ))
            await message.answer(response_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        else:
            await message.answer(response_text, parse_mode="Markdown")
    else:
        await message.answer("❌ Информация временно недоступна.")


async def _apply_placeholders(response_text: str) -> str:
    loyalty_percentage = await get_setting('loyalty_percentage', settings.LOYALTY_PERCENTAGE)
    loyalty_max_spend_percentage = await get_setting('loyalty_max_spend_percentage', settings.LOYALTY_MAX_SPEND_PERCENTAGE)
    loyalty_expiration_days = await get_setting('loyalty_expiration_days', settings.LOYALTY_EXPIRATION_DAYS)
    replacements = {
        "{YCLIENTS_BOOKING_URL}": settings.YCLIENTS_BOOKING_URL,
        "{LOYALTY_PERCENTAGE}": str(int(float(loyalty_percentage) * 100)),
        "{LOYALTY_MAX_SPEND_PERCENTAGE}": str(int(float(loyalty_max_spend_percentage) * 100)),
        "{LOYALTY_EXPIRATION_DAYS}": str(int(loyalty_expiration_days)),
    }
    for placeholder, value in replacements.items():
        if placeholder in response_text:
            response_text = response_text.replace(placeholder, value)
    return response_text


@router.message(F.text)
async def show_custom_button_response(message: types.Message):
    """Fallback для пользовательских кнопок из БД."""
    button_text = message.text or ""
    if not button_text:
        return
    known_buttons = {
        "📅 Записаться",
        "👤 Мой профиль",
        "🌸 Наши услуги",
        "🎁 Бонусы",
        "📍 Контакты",
        "💬 Поддержка",
        "⚙️ Админка",
    }
    if button_text in known_buttons:
        return
    try:
        res = await supabase.table("bot_buttons")\
            .select("*")\
            .eq("button_text", button_text)\
            .eq("is_active", True)\
            .single()\
            .execute()
        button = res.data if res.data else None
        if not button:
            return
        handler_type = (button.get("handler_type") or "info").lower()
        if handler_type == "book":
            from bot.handlers.book import open_booking
            await open_booking(message)
            return
        if handler_type == "profile":
            from bot.handlers.profile import show_profile
            await show_profile(message)
            return
        if handler_type == "admin":
            await show_admin_info(message)
            return
        response_text = button.get("response_text") or ""
        if not response_text:
            return
        response_text = await _apply_placeholders(response_text)
        await message.answer(response_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error handling custom button '{button_text}': {e}", exc_info=True)
