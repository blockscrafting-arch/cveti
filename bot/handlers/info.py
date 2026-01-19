"""
Обработчики информационных разделов бота
"""
from aiogram import Router, types, F
from bot.keyboards import get_contacts_inline_keyboard, get_services_inline_keyboard, get_support_inline_keyboard, get_button_response
from bot.config import settings
import logging

router = Router()
logger = logging.getLogger(__name__)


async def send_button_response(message: types.Message, button_text: str, inline_keyboard=None):
    """Отправляет ответ для кнопки, используя текст из БД"""
    response_text = await get_button_response(button_text)
    
    if response_text:
        # Заменяем переменные в тексте
        if "{YCLIENTS_BOOKING_URL}" in response_text:
            response_text = response_text.replace("{YCLIENTS_BOOKING_URL}", settings.YCLIENTS_BOOKING_URL)
        
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
    cashback_percent = int(settings.LOYALTY_PERCENTAGE * 100)
    response_text = await get_button_response("🎁 Бонусы")
    
    if response_text:
        # Заменяем процент кэшбека в тексте
        response_text = response_text.replace("{LOYALTY_PERCENTAGE}", str(cashback_percent))
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
