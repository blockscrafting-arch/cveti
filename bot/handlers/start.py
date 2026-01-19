from aiogram import Router, types
from aiogram.filters import CommandStart
from bot.keyboards import get_registration_keyboard, get_main_menu
from bot.services.supabase_client import supabase
from bot.config import settings
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    
    logger.info(f"Command /start from user {tg_id}")
    
    try:
        # Проверяем, есть ли пользователь в базе
        user_res = await supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        logger.info(f"User {tg_id} found in DB: {len(user_res.data) > 0}")
        
        if not user_res.data:
            # Если нет - просим телефон
            text = (
                "✨ **Добро пожаловать в студию красоты ЦВЕТИ!**\n\n"
                "Чтобы мы могли начислить вам приветственные баллы и показать ваш профиль, "
                "пожалуйста, поделитесь вашим номером телефона.\n\n"
                "📱 Нажмите кнопку ниже, чтобы поделиться номером:"
            )
            await message.answer(
                text,
                reply_markup=get_registration_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если есть - показываем главное меню
            user = user_res.data[0]
            is_admin = tg_id in settings.ADMIN_IDS
            
            text = (
                f"✨ **Рады видеть вас снова, {user.get('name', 'красотка')}!**\n\n"
                f"💰 **Ваш баланс:** {user.get('balance', 0)} баллов\n\n"
                "Выберите действие из меню ниже:"
            )
            
            await message.answer(
                text,
                reply_markup=await get_main_menu(is_admin=is_admin),
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
