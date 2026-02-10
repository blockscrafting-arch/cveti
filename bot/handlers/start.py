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
    
    logger.debug("tg_start entry user=%s contact=%s", tg_id, bool(message.contact))

    try:
        logger.debug("tg_start db_lookup start")
        # Проверяем, есть ли пользователь в базе
        user_res = await supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        logger.info("User %s found in DB: %s", tg_id, len(user_res.data) > 0)
        logger.debug("tg_start db_lookup done found=%s", bool(user_res.data))

        if not user_res.data:
            # Если нет - просим телефон
            text = (
                "✨ **Добро пожаловать в студию красоты ЦВЕТИ!**\n\n"
                "Чтобы мы могли начислить вам приветственные баллы и показать ваш профиль, "
                "пожалуйста, поделитесь вашим номером телефона.\n\n"
                "📱 Нажмите кнопку ниже, чтобы поделиться номером:"
            )
            logger.debug("tg_start sending registration prompt")
            await message.answer(
                text,
                reply_markup=get_registration_keyboard(),
                parse_mode="Markdown"
            )
            logger.debug("tg_start registration prompt sent")

        else:
            # Если есть - показываем главное меню
            user = user_res.data[0]
            is_admin = tg_id in settings.ADMIN_IDS
            
            text = (
                f"✨ **Рады видеть вас снова, {user.get('name', 'красотка')}!**\n\n"
                f"💰 **Ваш баланс:** {user.get('balance', 0)} баллов\n\n"
                "Выберите действие из меню ниже:"
            )
            
            logger.debug("tg_start sending main menu")
            await message.answer(
                text,
                reply_markup=await get_main_menu(is_admin=is_admin),
                parse_mode="Markdown"
            )
            logger.debug("tg_start main menu sent")

    except Exception as e:
        logger.debug("tg_start error type=%s", type(e).__name__)
        logger.error("Start handler failed: %s", e, exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
