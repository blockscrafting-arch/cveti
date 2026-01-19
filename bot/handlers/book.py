from aiogram import Router, types, F
from bot.config import settings
from bot.keyboards import get_main_menu
from bot.services.supabase_client import supabase
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📅 Записаться")
async def open_booking(message: types.Message):
    """Обработка кнопки 'Записаться'"""
    tg_id = message.from_user.id
    
    try:
        # Проверяем, зарегистрирован ли пользователь
        user_res = await supabase.table("users").select("id").eq("tg_id", tg_id).execute()
        is_registered = len(user_res.data) > 0
        
        # Получаем текст ответа из БД
        from bot.keyboards import get_button_response
        response_text = await get_button_response("📅 Записаться")
        
        if settings.BASE_URL.startswith("https://"):
            # Если есть HTTPS - открываем Mini App
            if not response_text:
                response_text = "📅 **Онлайн-запись**\n\nНажмите кнопку ниже, чтобы открыть календарь записи:"
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(
                text="📱 Открыть календарь записи",
                web_app=types.WebAppInfo(url=f"{settings.BASE_URL}/webapp")
            ))
            
            await message.answer(
                response_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
        else:
            # Если нет HTTPS - открываем прямую ссылку на YClients
            yclients_url = settings.YCLIENTS_BOOKING_URL
            if not response_text:
                response_text = (
                    "📅 **Онлайн-запись**\n\n"
                    f"Для записи перейдите по ссылке:\n{yclients_url}\n\n"
                    "💡 Для работы Mini App нужен HTTPS. Используйте ngrok для тестирования или настройте домен с SSL."
                )
            else:
                # Заменяем переменные в тексте
                response_text = response_text.replace("{YCLIENTS_BOOKING_URL}", yclients_url)
            
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(
                text="🌐 Открыть запись",
                url=yclients_url
            ))
            
            await message.answer(
                response_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error in open_booking: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка. Попробуйте еще раз.",
            parse_mode="Markdown"
        )
