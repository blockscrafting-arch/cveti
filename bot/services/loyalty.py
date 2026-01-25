"""
Логика системы лояльности: начисление баллов за платежи
Правила:
- 5% кэшбек с каждой оплаты (настраивается в админке)
- Баллы действуют 90 дней (3 месяца, настраивается в админке)
- Можно оплатить до 30% от суммы чека баллами (настраивается в админке)
- Списание по принципу FIFO (старые баллы первыми)
"""
from bot.services.supabase_client import supabase
from bot.services.phone_normalize import normalize_phone
from bot.services.settings import get_setting
from bot.services.yclients_api import yclients
from bot.config import settings
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def sync_user_with_yclients(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Синхронизирует данные пользователя с YClients:
    1. Ищет клиента в YClients по телефону
    2. Получает актуальный баланс и детали карты
    3. Обновляет данные в нашей базе
    4. Логирует изменения баланса если они произошли извне
    
    Returns:
        dict с ключами:
          - balance: актуальный баланс по данным YClients
          - diff: разница между балансом YClients и локальным балансом
    """
    try:
        # Получаем данные пользователя из нашей базы
        user_res = await supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_res.data:
            return None
        
        user = user_res.data[0]
        phone = user.get("phone")
        yclients_id = user.get("yclients_id")
        # Берем локальный баланс через RPC (учитывает истекшие баллы)
        old_balance = user.get("balance") or 0
        try:
            old_balance = await get_user_available_balance(user_id)
        except Exception as balance_err:
            logger.warning(f"Could not get available balance for user {user_id}, fallback to users.balance: {balance_err}")
        
        # 1. Если нет yclients_id, ищем по телефону
        if not yclients_id and phone:
            client = await yclients.get_client_by_phone(phone)
            if client:
                yclients_id = client.get("id")
                # Сохраняем найденный ID
                await supabase.table("users").update({"yclients_id": yclients_id}).eq("id", user_id).execute()
        
        if not yclients_id:
            logger.warning(f"Could not find YClients ID for user {user_id}")
            return None

        # 2. Получаем информацию о лояльности
        loyalty_info = await yclients.get_client_loyalty_info(yclients_id)
        if loyalty_info:
            # Извлекаем данные карты
            card_number = loyalty_info.get("number")
            card_status = "Бонусная карта"
            if "type" in loyalty_info and isinstance(loyalty_info["type"], dict):
                card_status = loyalty_info["type"].get("title", card_status)

            # Извлекаем баланс
            balance = 0
            if "points" in loyalty_info:
                balance = loyalty_info["points"]
            elif "balance" in loyalty_info:
                balance = loyalty_info["balance"]
            elif "card" in loyalty_info and isinstance(loyalty_info["card"], dict):
                balance = loyalty_info["card"].get("points") or loyalty_info["card"].get("balance", 0)
            elif "bonus" in loyalty_info:
                balance = loyalty_info["bonus"]
            
            try:
                balance = int(float(balance)) if balance else 0
            except (ValueError, TypeError):
                balance = 0
            
            # 3. Если баланс изменился извне (не через нашу систему), логируем это и корректируем FIFO
            diff = balance - old_balance
            if diff != 0:
                expiration_days = await get_setting('loyalty_expiration_days', settings.LOYALTY_EXPIRATION_DAYS)
                
                try:
                    # Используем RPC для атомарной корректировки баланса и FIFO-остатков
                    await supabase.rpc("adjust_loyalty_balance", {
                        "p_user_id": user_id,
                        "p_amount": diff,
                        "p_description": f"Синхронизация с YClients ({'+' if diff > 0 else ''}{diff} баллов)",
                        "p_expiration_days": expiration_days
                    }).execute()
                    logger.info(f"Balance adjusted via sync for user {user_id}: {diff}")
                except Exception as sync_err:
                    logger.error(f"Error calling adjust_loyalty_balance for user {user_id}: {sync_err}")
                    # Fallback на простое обновление если RPC не сработал
                    await supabase.table("users").update({"balance": balance}).eq("id", user_id).execute()
            else:
                # Если локальный баланс мог устареть (например, истекли баллы), обновляем его
                if user.get("balance") != old_balance:
                    await supabase.table("users").update({
                        "balance": old_balance,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", user_id).execute()

            # 4. Обновляем дополнительные поля (номер карты, статус, время синхронизации)
            await supabase.table("users").update({
                "loyalty_card_number": card_number,
                "loyalty_status": card_status,
                "loyalty_last_sync": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            logger.debug(f"Synced user {user_id}: balance={balance}, card={card_number}")
            return {"balance": balance, "diff": diff}
        else:
            logger.debug(f"No loyalty info found for user {user_id} (yclients_id: {yclients_id})")
            
    except Exception as e:
        logger.error(f"Error syncing user {user_id} with YClients: {e}", exc_info=True)
    
    return None

async def calculate_points(amount: float, percentage: Optional[float] = None) -> int:
    """Рассчитывает количество баллов (использует настройки из БД)"""
    if percentage is None:
        # Получаем процент из БД, fallback на config.py
        percentage = await get_setting('loyalty_percentage', settings.LOYALTY_PERCENTAGE)
    return int(amount * percentage)

async def process_loyalty_payment(phone: str, amount: float, visit_id: int):
    """
    Основная логика:
    1. Поиск клиента по телефону
    2. Синхронизация с YClients как источником истины
    3. Возвращаем разницу баланса для уведомления
    
    Защита от race condition:
    - Используем UNIQUE constraint на visit_id в БД
    - При попытке вставить дубликат получаем ошибку и возвращаем сообщение
    """
    try:
        normalized = normalize_phone(phone)
        
        if not normalized:
            return None, "Некорректный номер телефона"
        
        # Ищем пользователя
        user_res = await supabase.table("users").select("*").eq("phone", normalized).execute()
        
        if not user_res.data:
            logger.warning(f"User not found for phone: {normalized}")
            return None, "Пользователь не найден в системе"
        
        user = user_res.data[0]
        # YClients является источником истины по балансу
        sync_result = await sync_user_with_yclients(user["id"])
        if not sync_result:
            logger.warning(f"YClients sync failed for user {user['id']} (visit_id: {visit_id})")
            return None, "Не удалось синхронизировать баланс с YClients"
        
        diff = int(sync_result.get("diff") or 0)
        points_awarded = max(diff, 0)
        logger.info(
            f"YClients sync after payment: user_id={user['id']}, visit_id={visit_id}, "
            f"diff={diff}, awarded={points_awarded}"
        )
        return user["tg_id"], points_awarded
        
    except Exception as e:
        logger.error(f"Error in process_loyalty_payment: {e}", exc_info=True)
        return None, f"Ошибка обработки платежа: {str(e)}"


async def get_user_available_balance(user_id: int) -> int:
    """
    Получает актуальный баланс пользователя (только не истекшие баллы)
    Использует SQL-функцию get_user_available_balance
    """
    try:
        result = await supabase.rpc("get_user_available_balance", {
            "p_user_id": user_id
        }).execute()
        
        if result.data is not None:
            return int(result.data)
        return 0
    except Exception as e:
        logger.error(f"Error getting available balance for user {user_id}: {e}", exc_info=True)
        # Fallback: простой расчет через Python (менее точный, но работает)
        try:
            transactions = await supabase.table("loyalty_transactions")\
                .select("remaining_amount")\
                .eq("user_id", user_id)\
                .eq("transaction_type", "earn")\
                .gt("expires_at", datetime.utcnow().isoformat())\
                .gt("remaining_amount", 0)\
                .execute()
            
            if transactions.data:
                return sum(t.get("remaining_amount", 0) for t in transactions.data)
            return 0
        except Exception as fallback_error:
            logger.error(f"Fallback balance calculation also failed: {fallback_error}")
            return 0


async def spend_loyalty_points(
    user_id: int, 
    amount_to_spend: int, 
    total_bill_amount: int,
    description: Optional[str] = None
) -> Tuple[bool, str, Optional[int]]:
    """
    Списывает баллы по принципу FIFO с проверкой лимита 30% от суммы чека
    
    Args:
        user_id: ID пользователя
        amount_to_spend: Количество баллов для списания
        total_bill_amount: Общая сумма чека
        description: Описание транзакции (опционально)
    
    Returns:
        Tuple[success: bool, message: str, remaining_balance: Optional[int]]
    """
    try:
        # Получаем лимит списания из БД (fallback на config.py)
        max_spend_percentage = await get_setting('loyalty_max_spend_percentage', settings.LOYALTY_MAX_SPEND_PERCENTAGE)
        
        result = await supabase.rpc("spend_loyalty_points", {
            "p_user_id": user_id,
            "p_amount_to_spend": amount_to_spend,
            "p_total_bill_amount": total_bill_amount,
            "p_max_spend_percentage": max_spend_percentage,
            "p_description": description or f"Списание {amount_to_spend} баллов"
        }).execute()
        
        if result.data and result.data.get("success"):
            remaining = result.data.get("remaining_balance", 0)
            return True, f"Списано {amount_to_spend} баллов. Остаток: {remaining}", remaining
        else:
            error_msg = result.data.get("error", "Неизвестная ошибка") if result.data else "Ошибка при списании баллов"
            return False, error_msg, None
            
    except Exception as e:
        logger.error(f"Error spending loyalty points: {e}", exc_info=True)
        return False, f"Ошибка при списании баллов: {str(e)}", None
