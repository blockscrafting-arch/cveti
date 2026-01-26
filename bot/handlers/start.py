from aiogram import Router, types
from aiogram.filters import CommandStart
from bot.keyboards import get_registration_keyboard, get_main_menu
from bot.services.supabase_client import supabase
from bot.config import settings
import logging
import json
import time

DEBUG_LOG_PATHS = [
    r"d:\vladexecute\proj\CVETI\.cursor\debug.log",
    "/app/debug.log",
    "/tmp/debug.log"
]

def _debug_log(payload: dict):
    try:
        payload.setdefault("sessionId", "debug-session")
        payload.setdefault("runId", "run1")
        payload["timestamp"] = int(time.time() * 1000)
        line = json.dumps(payload, ensure_ascii=False)
        for log_path in DEBUG_LOG_PATHS:
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                break
            except Exception:
                continue
    except Exception:
        pass

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    
    logger.info(f"Command /start from user {tg_id}")
    logger.info("Start handler received text=%s contact=%s", message.text, bool(message.contact))

    # region agent log
    _debug_log({
        "hypothesisId": "H3",
        "location": "bot/handlers/start.py:cmd_start.entry",
        "message": "start handler entry",
        "data": {
            "has_text": bool(message.text),
            "is_start": bool(message.text and message.text.startswith("/start")),
            "has_contact": message.contact is not None
        }
    })
    # endregion
    
    try:
        # Проверяем, есть ли пользователь в базе
        user_res = await supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        logger.info(f"User {tg_id} found in DB: {len(user_res.data) > 0}")

        # region agent log
        _debug_log({
            "hypothesisId": "H4",
            "location": "bot/handlers/start.py:cmd_start.db_lookup",
            "message": "db user lookup",
            "data": {
                "found_user": bool(user_res.data)
            }
        })
        # endregion
        
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

            # region agent log
            _debug_log({
                "hypothesisId": "H5",
                "location": "bot/handlers/start.py:cmd_start.reply_new",
                "message": "sent registration prompt",
                "data": {
                    "branch": "new"
                }
            })
            # endregion
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

            # region agent log
            _debug_log({
                "hypothesisId": "H5",
                "location": "bot/handlers/start.py:cmd_start.reply_existing",
                "message": "sent main menu",
                "data": {
                    "branch": "existing"
                }
            })
            # endregion
    except Exception as e:
        # region agent log
        _debug_log({
            "hypothesisId": "H4",
            "location": "bot/handlers/start.py:cmd_start.error",
            "message": "start handler error",
            "data": {
                "error_type": type(e).__name__
            }
        })
        # endregion
        logger.error("Start handler failed: %s", e, exc_info=True)
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
