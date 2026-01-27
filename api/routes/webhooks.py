from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Header, Query
from api.models.yclients import YClientsWebhookData
from bot.services.supabase_client import supabase
from bot.services.loyalty import process_loyalty_payment
from bot.services.notifications import send_loyalty_notification
from bot.config import settings
from bot.dispatcher import dp
from aiogram import Bot
from aiogram.types import Update
import logging

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
    secret_token: str = Header(None, alias="X-Webhook-Secret"),
    secret_token_query: str | None = Query(default=None, alias="secret_token")
):
    """Принимает вебхук и запускает обработку в фоне"""
    if not settings.WEBHOOK_SECRET:
        logger.error("WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    # Проверка безопасности
    if secret_token != settings.WEBHOOK_SECRET and secret_token_query != settings.WEBHOOK_SECRET:
        logger.warning("Unauthorized webhook attempt")
        raise HTTPException(status_code=403, detail="Invalid secret token")
    if secret_token_query and secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Webhook secret provided via query parameter")
    
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
    secret_token: str = Header(None, alias="X-Webhook-Secret"),
    secret_token_query: str | None = Query(default=None, alias="secret_token")
):
    """Обрабатывает уведомления об отключении интеграции от YCLIENTS"""
    if not settings.WEBHOOK_SECRET:
        logger.error("WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    if secret_token != settings.WEBHOOK_SECRET and secret_token_query != settings.WEBHOOK_SECRET:
        logger.warning("Unauthorized webhook callback attempt")
        raise HTTPException(status_code=403, detail="Invalid secret token")
    if secret_token_query and secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Webhook secret provided via query parameter")

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
async def telegram_webhook(
    request: Request,
    telegram_secret: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Вебхук от Telegram для получения обновлений бота.
    Telegram будет отправлять сюда все сообщения и события.
    """
    if _telegram_bot is None:
        logger.error("Telegram bot is not initialized")
        raise HTTPException(status_code=500, detail="Bot not ready")
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if telegram_secret != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Invalid Telegram webhook secret")
            raise HTTPException(status_code=403, detail="Invalid secret token")
    
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

        print(f"[tg_webhook] entry id={update_id} type={update_type} chat_id={chat_id} text={update_data.get('message', {}).get('text')}")

        # Создаем объект Update из данных с контекстом бота
        update = Update.model_validate(update_data, context={"bot": _telegram_bot})
        
        # Передаем обновление в Dispatcher для обработки
        print(f"[tg_webhook] dispatching id={update_id} type={update_type}")
        await dp.feed_update(_telegram_bot, update)
        print(f"[tg_webhook] dispatched id={update_id} type={update_type}")

        logger.debug(f"Telegram webhook processed: update_id={update.update_id}")
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        # Telegram ожидает {"ok": true} даже при ошибках, иначе будет повторять запрос
        return {"ok": False}
