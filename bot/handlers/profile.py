from aiogram import Router, types, F
from bot.services.supabase_client import supabase
from bot.services.phone_normalize import normalize_phone
from bot.services.settings import get_setting
from bot.services.loyalty import sync_user_with_yclients
from bot.keyboards import get_main_menu, get_profile_inline_keyboard
from bot.config import settings
import logging
from datetime import datetime, timedelta

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.contact)
async def handle_contact(message: types.Message):
    """Обработка полученного контакта для регистрации"""
    contact = message.contact
    phone = normalize_phone(contact.phone_number)
    tg_id = message.from_user.id
    name = contact.first_name or message.from_user.first_name or "Пользователь"
    
    logger.info(f"Received contact from {tg_id}, phone: {phone}, name: {name}")
    
    if not phone:
        await message.answer("Некорректный номер телефона. Попробуйте еще раз.")
        return
    
    try:
        # 1. Проверяем, может пользователь уже есть по телефону (но без tg_id)
        user_res = await supabase.table("users").select("*").eq("phone", phone).execute()
        
        if user_res.data:
            # Обновляем существующего
            user = user_res.data[0]
            await supabase.table("users").update({
                "tg_id": tg_id,
                "name": name,
                "active": True
            }).eq("id", user["id"]).execute()
            
            # Сразу синхронизируем баланс с YClients
            sync_result = await sync_user_with_yclients(user["id"])
            current_balance = sync_result.get("balance") if sync_result else user.get("balance", 0)
            
            text = (
                f"✨ **Ваш профиль найден!**\n\n"
                f"💰 **Баланс:** {current_balance} баллов\n\n"
                "Добро пожаловать обратно! Выберите действие из меню:"
            )
        else:
            # Создаем нового пользователя
            welcome_bonus = await get_setting('welcome_bonus_amount', 0)
            
            user_res = await supabase.table("users").insert({
                "tg_id": tg_id,
                "phone": phone,
                "name": name,
                "balance": welcome_bonus,
                "level": "new"
            }).execute()
            
            if not user_res.data:
                raise ValueError("Could not create user in database")
                
            user_id = user_res.data[0]["id"]
            
            # Начисляем приветственные баллы если они есть
            if welcome_bonus > 0:
                expiration_days = await get_setting('loyalty_expiration_days', settings.LOYALTY_EXPIRATION_DAYS)
                expires_at = datetime.utcnow() + timedelta(days=expiration_days)
                
                await supabase.table("loyalty_transactions").insert({
                    "user_id": user_id,
                    "amount": welcome_bonus,
                    "transaction_type": "earn",
                    "description": "Приветственный бонус",
                    "expires_at": expires_at.isoformat(),
                    "remaining_amount": welcome_bonus
                }).execute()
            
            # Пытаемся синхронизировать с YClients (возможно клиент уже там есть)
            sync_result = await sync_user_with_yclients(user_id)
            final_balance = sync_result.get("balance") if sync_result else welcome_bonus
            
            if welcome_bonus > 0:
                text = (
                    "🎉 **Вы успешно зарегистрированы!**\n\n"
                    "Добро пожаловать в программу лояльности студии красоты ЦВЕТИ!\n\n"
                    f"🎁 Вам начислено **{welcome_bonus} приветственных баллов**!\n\n"
                    f"💰 **Ваш баланс:** {final_balance} баллов\n\n"
                    "Баллы начисляются автоматически после каждого визита.\n"
                    "Выберите действие из меню:"
                )
            else:
                text = (
                    "🎉 **Вы успешно зарегистрированы!**\n\n"
                    "Добро пожаловать в программу лояльности студии красоты ЦВЕТИ!\n\n"
                    f"💰 **Ваш баланс:** {final_balance} баллов\n\n"
                    "Баллы начисляются автоматически после каждого визита.\n"
                    "Выберите действие из меню:"
                )

        # Показываем главное меню
        is_admin = tg_id in settings.ADMIN_IDS
        await message.answer(
            text,
            reply_markup=await get_main_menu(is_admin=is_admin),
            parse_mode="Markdown"
        )
        logger.info(f"User {tg_id} registered successfully")
    except Exception as e:
        logger.error(f"Error in handle_contact: {e}", exc_info=True)
        await message.answer("Произошла ошибка при регистрации. Попробуйте еще раз или напишите /start")

@router.message(F.text.in_(["👤 Мой профиль", "🌸 Мой профиль"]))
async def show_profile(message: types.Message):
    tg_id = message.from_user.id
    
    try:
        user_res = await supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        
        if not user_res.data:
            await message.answer(
                "❌ Пожалуйста, зарегистрируйтесь, нажав /start",
                parse_mode="Markdown"
            )
            return
            
        user = user_res.data[0]
        
        # Синхронизируем баланс перед показом
        sync_result = await sync_user_with_yclients(user["id"])
        current_balance = sync_result.get("balance") if sync_result else user.get("balance", 0)
        
        # Определяем уровень с эмодзи
        level_emoji = {
            "new": "🆕",
            "regular": "⭐",
            "vip": "💎"
        }
        level_text = {
            "new": "Новый",
            "regular": "Постоянный",
            "vip": "VIP"
        }
        level = user.get('level', 'new')
        
        text = (
            f"👤 **Мой профиль**\n\n"
            f"**Имя:** {user.get('name', 'Не указано')}\n"
            f"**Телефон:** {user.get('phone', 'Не указан')}\n"
            f"**Баланс:** {current_balance} баллов\n"
            f"**Уровень:** {level_emoji.get(level, '⭐')} {level_text.get(level, 'Новый')}\n\n"
            "💡 Вы можете использовать баллы для оплаты услуг в нашем салоне!\n\n"
            "📜 Нажмите кнопку ниже, чтобы посмотреть историю начислений:"
        )
        
        await message.answer(
            text,
            reply_markup=get_profile_inline_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in show_profile: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при загрузке профиля. Попробуйте еще раз.",
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "profile_history")
async def show_profile_history(callback: types.CallbackQuery):
    """Показывает историю транзакций пользователя"""
    tg_id = callback.from_user.id
    
    try:
        # Получаем пользователя
        user_res = await supabase.table("users").select("id").eq("tg_id", tg_id).execute()
        if not user_res.data:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        user_id = user_res.data[0]["id"]
        
        # Получаем последние транзакции
        transactions_res = await supabase.table("loyalty_transactions")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        
        transactions = transactions_res.data if transactions_res.data else []
        
        if not transactions:
            text = (
                "📜 **История баллов**\n\n"
                "У вас пока нет транзакций.\n\n"
                "Баллы начисляются автоматически после каждого визита!"
            )
        else:
            text = "📜 **История баллов**\n\n"
            for t in transactions:
                amount = t.get('amount', 0)
                description = t.get('description', 'Транзакция')
                created_at = t.get('created_at', '')
                
                # Форматируем дату
                try:
                    if created_at:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%d.%m.%Y %H:%M')
                    else:
                        date_str = 'Дата неизвестна'
                except:
                    date_str = 'Дата неизвестна'
                
                sign = "+" if amount > 0 else ""
                text += f"{sign}{amount} баллов\n"
                text += f"_{description}_\n"
                text += f"📅 {date_str}\n\n"
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_profile_inline_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as edit_error:
            # Если не удалось отредактировать (например, сообщение слишком старое),
            # отправляем новое сообщение
            logger.warning(f"Could not edit message, sending new one: {edit_error}")
            await callback.message.answer(
                text,
                reply_markup=get_profile_inline_keyboard(),
                parse_mode="Markdown"
            )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_profile_history: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке истории", show_alert=True)
