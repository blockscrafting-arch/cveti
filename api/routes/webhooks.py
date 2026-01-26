from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Header
from api.models.yclients import YClientsWebhookData
from bot.services.supabase_client import supabase
from bot.services.loyalty import process_loyalty_payment
from bot.services.notifications import send_loyalty_notification
from bot.config import settings
from bot.dispatcher import dp
from aiogram import Bot
from aiogram.types import Update
import logging
import json
import time

DEBUG_LOG_PATH = r"d:\vladexecute\proj\CVETI\.cursor\debug.log"

def _debug_log(payload: dict):
    try:
        payload.setdefault("sessionId", "debug-session")
        payload.setdefault("runId", "run1")
        payload["timestamp"] = int(time.time() * 1000)
        line = json.dumps(payload, ensure_ascii=False)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

router = APIRouter(prefix="/webhook", tags=["webhooks"])
logger = logging.getLogger(__name__)

# Глобальный Bot экземпляр для уведомлений и обработки webhook
_notification_bot: Bot = None
_telegram_bot: Bot = None

def set_notification_bot(bot: Bot):
    """Установить Bot экземпляр для уведомлений и webhook"""
    global _notification_bot, _telegram_bot
    _notification_bot = bot
    _telegram_bot = bot

async def handle_payment_webhook(payload: YClientsWebhookData):
    """Фоновая задача для обработки платежа"""
    webhook_id = str(payload.resource_id)
    
    try:
        data = payload.data
        
        # Валидация обязательных полей
        if not data:
            raise ValueError("Missing data field in webhook")
        
        client_data = data.get("client", {})
        client_phone = client_data.get("phone")
        amount = data.get("amount", 0)
        visit_id = data.get("visit_id")
        
        if not client_phone:
            raise ValueError("Missing client.phone in webhook data")
        
        if not amount or amount <= 0:
            raise ValueError(f"Invalid amount: {amount}")
        
        if not visit_id:
            raise ValueError("Missing visit_id in webhook data")
        
        # 1. Логируем в БД, что получили вебхук
        try:
            await supabase.table("webhook_log").insert({
                "webhook_id": webhook_id,
                "phone": client_phone,
                "amount": amount,
                "status": "received"
            }).execute()
        except Exception as e:
            logger.error(f"Error logging webhook: {e}")
            # Продолжаем обработку даже если логирование не удалось
        
        # 2. Обрабатываем лояльность
        tg_id, result = await process_loyalty_payment(client_phone, amount, visit_id)
        
        if isinstance(result, str) or result is None:
            # result содержит сообщение об ошибке
            error_msg = result if isinstance(result, str) else "Unknown error"
            try:
                await supabase.table("webhook_log").update({
                    "status": "failed",
                    "error_message": error_msg
                }).eq("webhook_id", webhook_id).execute()
            except Exception as e:
                logger.error(f"Error updating webhook log: {e}")
            
            logger.warning(f"Failed to process webhook {webhook_id}: {error_msg}")
        else:
            points = int(result)
            # Отправляем уведомление в Телеграм только при начислении
            if tg_id and points > 0:
                if _notification_bot:
                    await send_loyalty_notification(_notification_bot, tg_id, points)
                else:
                    logger.warning("Notification bot not set, skipping notification")
            
            try:
                await supabase.table("webhook_log").update({
                    "status": "processed"
                }).eq("webhook_id", webhook_id).execute()
            except Exception as e:
                logger.error(f"Error updating webhook log: {e}")
            
            if points > 0:
                logger.info(f"Processed points for {client_phone}: +{points}")
            else:
                logger.info(f"Webhook processed for {client_phone}: no balance change")
            
    except Exception as e:
        logger.error(f"Error processing webhook {webhook_id}: {e}", exc_info=True)
        try:
            await supabase.table("webhook_log").update({
                "status": "failed",
                "error_message": str(e)
            }).eq("webhook_id", webhook_id).execute()
        except Exception as log_error:
            logger.error(f"Error logging webhook error: {log_error}")

@router.post("/yclients")
async def yclients_webhook(
    payload: YClientsWebhookData, 
    background_tasks: BackgroundTasks,
    secret_token: str = Header(None, alias="X-Webhook-Secret")
):
    """Принимает вебхук и запускает обработку в фоне"""
    # Проверка безопасности
    if secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Unauthorized webhook attempt")
        raise HTTPException(status_code=403, detail="Invalid secret token")
    
    # Базовая валидация структуры
    if not payload.data:
        logger.warning("Webhook received without data field")
        raise HTTPException(status_code=400, detail="Missing data field")
    
    # Мы отвечаем YClients "200 OK" сразу, чтобы они не слали повторно, 
    # а тяжелую логику делаем в фоне (BackgroundTasks)
    background_tasks.add_task(handle_payment_webhook, payload)
    return {"status": "accepted"}

@router.post("/yclients/callback")
async def yclients_callback(
    payload: dict,
    background_tasks: BackgroundTasks,
    secret_token: str = Header(None, alias="X-Webhook-Secret")
):
    """Обрабатывает уведомления об отключении интеграции от YCLIENTS"""
    if secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Unauthorized webhook callback attempt")
        raise HTTPException(status_code=403, detail="Invalid secret token")

    logger.info(f"YClients callback received: {payload}")
    
    # Логируем событие отключения
    try:
        resource_id = payload.get('resource_id', 'unknown')
        await supabase.table("webhook_log").insert({
            "webhook_id": f"callback_{resource_id}",
            "status": "disconnected",
            "phone": None,
            "amount": 0
        }).execute()
        logger.info(f"Integration disconnect logged for resource_id: {resource_id}")
    except Exception as e:
        logger.error(f"Error logging disconnect: {e}")
    
    return {"status": "ok"}

@router.post("/telegram")
async def telegram_webhook(request: Request):
    """
    Вебхук от Telegram для получения обновлений бота.
    Telegram будет отправлять сюда все сообщения и события.
    """
    if _telegram_bot is None:
        logger.error("Telegram bot is not initialized")
        raise HTTPException(status_code=500, detail="Bot not ready")
    
    try:
        # Получаем JSON от Telegram
        update_data = await request.json()
        update_id = update_data.get("update_id")
        chat_id = None
        update_type = None
        if "message" in update_data:
            update_type = "message"
            chat_id = update_data.get("message", {}).get("chat", {}).get("id")
        elif "callback_query" in update_data:
            update_type = "callback_query"
            chat_id = update_data.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")
        elif "my_chat_member" in update_data:
            update_type = "my_chat_member"
            chat_id = update_data.get("my_chat_member", {}).get("chat", {}).get("id")

        logger.info(
            "Telegram update received: id=%s type=%s chat_id=%s",
            update_id,
            update_type,
            chat_id
        )

        # region agent log
        _debug_log({
            "hypothesisId": "H1",
            "location": "api/routes/webhooks.py:telegram_webhook.entry",
            "message": "webhook entry",
            "data": {
                "has_bot": _telegram_bot is not None,
                "update_type": update_type,
                "has_text": bool(update_data.get("message", {}).get("text")),
                "is_start": update_data.get("message", {}).get("text", "").startswith("/start")
            }
        })
        # endregion

        # Создаем объект Update из данных с контекстом бота
        update = Update.model_validate(update_data, context={"bot": _telegram_bot})
        
        # Передаем обновление в Dispatcher для обработки
        await dp.feed_update(_telegram_bot, update)

        # region agent log
        _debug_log({
            "hypothesisId": "H2",
            "location": "api/routes/webhooks.py:telegram_webhook.feed_update",
            "message": "feed_update ok",
            "data": {
                "update_type": update_type
            }
        })
        # endregion
        
        logger.debug(f"Telegram webhook processed: update_id={update.update_id}")
        return {"ok": True}
        
    except Exception as e:
        # region agent log
        _debug_log({
            "hypothesisId": "H2",
            "location": "api/routes/webhooks.py:telegram_webhook.error",
            "message": "webhook error",
            "data": {
                "error_type": type(e).__name__
            }
        })
        # endregion
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        # Telegram ожидает {"ok": true} даже при ошибках, иначе будет повторять запрос
        return {"ok": False}
