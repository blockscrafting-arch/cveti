from fastapi import APIRouter, Header, HTTPException, Depends, Query, BackgroundTasks, UploadFile, File, Form
from bot.services.auth import validate_init_data, get_user_id_from_init_data
from bot.services.supabase_client import supabase
from bot.services.notifications import send_broadcast_message
from bot.services.storage import get_storage_service
from bot.config import settings
from typing import Optional, List, Dict, Any
from aiogram import Bot
import logging
import json
import os
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)

# Глобальный Bot экземпляр для рассылок
_broadcast_bot: Bot = None

def set_broadcast_bot(bot: Bot):
    """Установить Bot экземпляр для рассылок"""
    global _broadcast_bot
    _broadcast_bot = bot

async def get_current_admin(x_tg_init_data: Optional[str] = Header(None)):
    """Проверяет, является ли пользователь администратором"""
    try:
        if not x_tg_init_data or not validate_init_data(x_tg_init_data):
            raise HTTPException(status_code=401, detail="Invalid initData")
            
        tg_id = get_user_id_from_init_data(x_tg_init_data)
        if not tg_id or tg_id not in settings.ADMIN_IDS:
            logger.warning(f"Unauthorized admin access attempt: tg_id={tg_id}")
            raise HTTPException(status_code=403, detail="Admin access denied")
        
        return tg_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_admin: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# --- File Upload ---

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form(default="images"),
    x_tg_init_data: Optional[str] = Header(None),
    _: int = Depends(get_current_admin)
):
    """Загружает файл в Supabase Storage"""
    try:
        # Проверяем тип файла
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are allowed")
        
        # Читаем содержимое файла
        file_content = await file.read()
        
        # Проверяем размер файла (максимум 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
        
        # Загружаем в Supabase Storage
        storage_service = get_storage_service()
        public_url = await storage_service.upload_file(
            file_content=file_content,
            filename=file.filename or "image.jpg",
            folder=folder
        )
        
        if not public_url:
            raise HTTPException(status_code=500, detail="Failed to upload file")
        
        return {
            "url": public_url,
            "filename": file.filename,
            "size": len(file_content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# --- Masters ---

@router.get("/masters")
async def get_masters(_: int = Depends(get_current_admin)):
    try:
        # Сортируем по order, затем по id для стабильности
        res = await supabase.table("masters").select("*").order("order").order("id").execute()
        return res.data if res.data else []
    except Exception as e:
        # Если поле order не существует, сортируем по name
        logger.warning(f"Order field may not exist, trying fallback: {e}")
        try:
            res = await supabase.table("masters").select("*").order("name").execute()
            return res.data if res.data else []
        except Exception as e2:
            logger.error(f"Error in get_masters: {e2}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database error: {str(e2)}")

@router.post("/masters")
async def create_master(data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        # Если order не указан, ставим максимальный + 1
        if "order" not in data or data["order"] is None:
            max_res = await supabase.table("masters").select("order").order("order", desc=True).limit(1).execute()
            max_order = max_res.data[0]["order"] if max_res.data and max_res.data[0].get("order") is not None else 0
            data["order"] = max_order + 1
        
        res = await supabase.table("masters").insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in create_master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/masters/{id}")
async def update_master(id: int, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("masters").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/masters/{id}")
async def delete_master(id: int, _: int = Depends(get_current_admin)):
    try:
        await supabase.table("masters").delete().eq("id", id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in delete_master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/masters/{id}/move")
async def move_master(id: int, direction: str = Query(..., pattern="^(up|down)$"), _: int = Depends(get_current_admin)):
    """Перемещает мастера вверх или вниз по порядку"""
    try:
        # Получаем текущий элемент
        current_res = await supabase.table("masters").select("*").eq("id", id).single().execute()
        current_order = current_res.data.get("order")
        
        # Если order равен None, устанавливаем его на основе id
        if current_order is None:
            # Получаем все записи и находим максимальный order
            all_res = await supabase.table("masters").select("*").execute()
            max_order = 0
            if all_res.data:
                for item in all_res.data:
                    item_order = item.get("order")
                    if item_order is not None and item_order > max_order:
                        max_order = item_order
            current_order = max_order + 1
            await supabase.table("masters").update({"order": current_order}).eq("id", id).execute()
        
        # Получаем все записи для поиска соседа
        all_res = await supabase.table("masters").select("*").execute()
        valid_items = [item for item in all_res.data if item.get("order") is not None]
        
        # Определяем направление и новый порядок
        # "up" = переместить выше в списке = уменьшить свой order = найти соседа с МЕНЬШИМ order
        # "down" = переместить ниже в списке = увеличить свой order = найти соседа с БОЛЬШИМ order
        if direction == "up":
            # Ищем соседа сверху (order меньше текущего)
            candidates = [item for item in valid_items if item.get("id") != id and item.get("order") is not None and item.get("order") < current_order]
            if candidates:
                # Берем ближайшего сверху (максимальный из тех, что меньше)
                target = max(candidates, key=lambda x: x.get("order", 0))
                target_res = type('obj', (object,), {'data': [target]})()
            else:
                target_res = type('obj', (object,), {'data': []})()
        else:  # down
            # Ищем соседа снизу (order больше текущего)
            candidates = [item for item in valid_items if item.get("id") != id and item.get("order") is not None and item.get("order") > current_order]
            if candidates:
                # Берем ближайшего снизу (минимальный из тех, что больше)
                target = min(candidates, key=lambda x: x.get("order", 0))
                target_res = type('obj', (object,), {'data': [target]})()
            else:
                target_res = type('obj', (object,), {'data': []})()
        
        if not target_res.data:
            return {"status": "ok", "message": "Already at edge"}
        
        target = target_res.data[0]
        target_order = target.get("order")
        
        if target_order is None:
            # Если у целевого элемента тоже нет order, устанавливаем его
            target_order = target["id"]
            await supabase.table("masters").update({"order": target_order}).eq("id", target["id"]).execute()
        
        # Меняем местами
        await supabase.table("masters").update({"order": target_order}).eq("id", id).execute()
        await supabase.table("masters").update({"order": current_order}).eq("id", target["id"]).execute()
        
        # Проверяем, что данные действительно обновились
        verify_res = await supabase.table("masters").select("id,order").in_("id", [id, target["id"]]).execute()
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in move_master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- Services ---

@router.get("/services")
async def get_services(_: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("services").select("*").order("order").order("id").execute()
        return res.data if res.data else []
    except Exception as e:
        # Если поле order не существует, сортируем по title
        logger.warning(f"Order field may not exist, trying fallback: {e}")
        try:
            res = await supabase.table("services").select("*").order("title").execute()
            return res.data if res.data else []
        except Exception as e2:
            logger.error(f"Error in get_services: {e2}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database error: {str(e2)}")

@router.post("/services")
async def create_service(data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        # Если order не указан, ставим максимальный + 1
        if "order" not in data or data["order"] is None:
            max_res = await supabase.table("services").select("order").order("order", desc=True).limit(1).execute()
            max_order = max_res.data[0]["order"] if max_res.data and max_res.data[0].get("order") is not None else 0
            data["order"] = max_order + 1
        
        res = await supabase.table("services").insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in create_service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/services/{id}")
async def update_service(id: int, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("services").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/services/{id}")
async def delete_service(id: int, _: int = Depends(get_current_admin)):
    try:
        await supabase.table("services").delete().eq("id", id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in delete_service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/services/{id}/move")
async def move_service(id: int, direction: str = Query(..., pattern="^(up|down)$"), _: int = Depends(get_current_admin)):
    """Перемещает услугу вверх или вниз по порядку"""
    try:
        current_res = await supabase.table("services").select("*").eq("id", id).single().execute()
        if not current_res.data:
            raise HTTPException(status_code=404, detail="Service not found")
        
        current_order = current_res.data.get("order")
        
        # Если order равен None, устанавливаем его
        if current_order is None:
            all_res = await supabase.table("services").select("*").execute()
            max_order = 0
            if all_res.data:
                for item in all_res.data:
                    item_order = item.get("order")
                    if item_order is not None and item_order > max_order:
                        max_order = item_order
            current_order = max_order + 1
            await supabase.table("services").update({"order": current_order}).eq("id", id).execute()
        
        # Получаем все записи для поиска соседа
        all_res = await supabase.table("services").select("*").execute()
        valid_items = [item for item in all_res.data if item.get("order") is not None]
        
        # "up" = переместить выше = уменьшить свой order = найти соседа с МЕНЬШИМ order
        # "down" = переместить ниже = увеличить свой order = найти соседа с БОЛЬШИМ order
        if direction == "up":
            candidates = [item for item in valid_items if item.get("id") != id and item.get("order") is not None and item.get("order") < current_order]
            if candidates:
                target = max(candidates, key=lambda x: x.get("order", 0))
                target_res = type('obj', (object,), {'data': [target]})()
            else:
                target_res = type('obj', (object,), {'data': []})()
        else:
            candidates = [item for item in valid_items if item.get("id") != id and item.get("order") is not None and item.get("order") > current_order]
            if candidates:
                target = min(candidates, key=lambda x: x.get("order", 0))
                target_res = type('obj', (object,), {'data': [target]})()
            else:
                target_res = type('obj', (object,), {'data': []})()
        
        if not target_res.data:
            return {"status": "ok", "message": "Already at edge"}
        
        target = target_res.data[0]
        target_order = target.get("order")
        
        if target_order is None:
            target_order = target["id"]
            await supabase.table("services").update({"order": target_order}).eq("id", target["id"]).execute()
        
        await supabase.table("services").update({"order": target_order}).eq("id", id).execute()
        await supabase.table("services").update({"order": current_order}).eq("id", target["id"]).execute()
        
        # Проверяем, что данные действительно обновились
        verify_res = await supabase.table("services").select("id,order").in_("id", [id, target["id"]]).execute()
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in move_service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- Promotions ---

@router.get("/promotions")
async def get_promotions(_: int = Depends(get_current_admin)):
    try:
        # Пробуем сортировать по order, если поле существует
        res = await supabase.table("promotions").select("*").order("order").order("id").execute()
        return res.data if res.data else []
    except Exception as e:
        # Если поле order не существует, сортируем по id
        logger.warning(f"Order field may not exist, trying fallback: {e}")
        try:
            res = await supabase.table("promotions").select("*").order("id", desc=True).execute()
            return res.data if res.data else []
        except Exception as e2:
            logger.error(f"Error in get_promotions: {e2}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database error: {str(e2)}")

@router.post("/promotions")
async def create_promotion(data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        # Если order не указан, ставим максимальный + 1
        if "order" not in data or data["order"] is None:
            max_res = await supabase.table("promotions").select("order").order("order", desc=True).limit(1).execute()
            max_order = max_res.data[0]["order"] if max_res.data and max_res.data[0].get("order") is not None else 0
            data["order"] = max_order + 1
        
        res = await supabase.table("promotions").insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in create_promotion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/promotions/{id}")
async def update_promotion(id: int, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("promotions").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_promotion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/promotions/{id}")
async def delete_promotion(id: int, _: int = Depends(get_current_admin)):
    try:
        await supabase.table("promotions").delete().eq("id", id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in delete_promotion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/promotions/{id}/move")
async def move_promotion(id: int, direction: str = Query(..., pattern="^(up|down)$"), _: int = Depends(get_current_admin)):
    """Перемещает акцию вверх или вниз по порядку"""
    try:
        current_res = await supabase.table("promotions").select("*").eq("id", id).single().execute()
        if not current_res.data:
            raise HTTPException(status_code=404, detail="Promotion not found")
        
        current_order = current_res.data.get("order")
        
        # Если order равен None, устанавливаем его
        if current_order is None:
            all_res = await supabase.table("promotions").select("*").execute()
            max_order = 0
            if all_res.data:
                for item in all_res.data:
                    item_order = item.get("order")
                    if item_order is not None and item_order > max_order:
                        max_order = item_order
            current_order = max_order + 1
            await supabase.table("promotions").update({"order": current_order}).eq("id", id).execute()
        
        # Получаем все записи для поиска соседа
        all_res = await supabase.table("promotions").select("*").execute()
        valid_items = [item for item in all_res.data if item.get("order") is not None]
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                json.dump({"location":"admin.py:505","message":"Valid promotions found","data":{"total_items":len(all_res.data) if all_res.data else 0,"valid_count":len(valid_items),"current_order":current_order},"timestamp":int(datetime.now().timestamp()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}, f, ensure_ascii=False)
                f.write('\n')
        except: pass
        # #endregion
        
        # "up" = переместить выше = уменьшить свой order = найти соседа с МЕНЬШИМ order
        # "down" = переместить ниже = увеличить свой order = найти соседа с БОЛЬШИМ order
        if direction == "up":
            candidates = [item for item in valid_items if item.get("id") != id and item.get("order") is not None and item.get("order") < current_order]
            if candidates:
                target = max(candidates, key=lambda x: x.get("order", 0))
                target_res = type('obj', (object,), {'data': [target]})()
            else:
                target_res = type('obj', (object,), {'data': []})()
        else:
            candidates = [item for item in valid_items if item.get("id") != id and item.get("order") is not None and item.get("order") > current_order]
            if candidates:
                target = min(candidates, key=lambda x: x.get("order", 0))
                target_res = type('obj', (object,), {'data': [target]})()
            else:
                target_res = type('obj', (object,), {'data': []})()
        
        if not target_res.data:
            return {"status": "ok", "message": "Already at edge"}
        
        target = target_res.data[0]
        target_order = target.get("order")
        
        if target_order is None:
            target_order = target["id"]
            await supabase.table("promotions").update({"order": target_order}).eq("id", target["id"]).execute()
        
        await supabase.table("promotions").update({"order": target_order}).eq("id", id).execute()
        await supabase.table("promotions").update({"order": current_order}).eq("id", target["id"]).execute()
        
        # Проверяем, что данные действительно обновились
        verify_res = await supabase.table("promotions").select("id,order").in_("id", [id, target["id"]]).execute()
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in move_promotion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- Users ---

@router.get("/users")
async def get_users(_: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("users").select("*").order("created_at", desc=True).execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error in get_users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/users/{id}")
async def get_user(id: int, _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("users").select("*").eq("id", id).single().execute()
        return res.data if res.data else {}
    except Exception as e:
        logger.error(f"Error in get_user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/users/{id}")
async def update_user(id: int, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        # Удаляем updated_at из данных, если он там есть - БД обновит автоматически через триггер или DEFAULT
        data.pop("updated_at", None)
        res = await supabase.table("users").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- Transactions ---

@router.get("/users/{user_id}/transactions")
async def get_user_transactions(user_id: int, _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("loyalty_transactions")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(50)\
            .execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error in get_user_transactions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/users/{user_id}/transactions")
async def create_transaction(user_id: int, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    """Создает транзакцию и обновляет баланс пользователя"""
    try:
        # Получаем текущий баланс пользователя
        user_res = await supabase.table("users").select("balance").eq("id", user_id).single().execute()
        if not user_res.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_balance = user_res.data["balance"]
        amount = data.get("amount", 0)
        new_balance = current_balance + amount
        
        # Создаем транзакцию
        transaction_data = {
            "user_id": user_id,
            "amount": amount,
            "transaction_type": "earn" if amount > 0 else "spend",
            "description": data.get("description", "Ручное изменение баланса"),
            "visit_id": None
        }
        
        res = await supabase.table("loyalty_transactions").insert(transaction_data).execute()
        
        # Обновляем баланс пользователя
        await supabase.table("users").update({"balance": new_balance}).eq("id", user_id).execute()
        
        return res.data[0] if res.data else {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_transaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- Broadcasts ---

async def check_scheduled_broadcasts():
    """Проверяет запланированные рассылки и запускает те, у которых наступило время"""
    try:
        # Используем UTC время для сравнения, так как scheduled_at хранится в UTC
        from datetime import timezone
        now = datetime.now(timezone.utc)
        # Ищем рассылки со статусом 'scheduled' где scheduled_at <= now()
        # Форматируем дату для Supabase (ISO формат с Z для UTC)
        now_str = now.strftime('%Y-%m-%dT%H:%M:%S')
        
        res = await supabase.table("broadcasts")\
            .select("*")\
            .eq("status", "scheduled")\
            .lte("scheduled_at", now_str)\
            .execute()
        
        if res.data:
            logger.info(f"Found {len(res.data)} scheduled broadcasts to send")
            for broadcast in res.data:
                broadcast_id = broadcast["id"]
                # Меняем статус на pending и запускаем отправку
                await supabase.table("broadcasts").update({
                    "status": "pending",
                    "scheduled_at": None  # Убираем запланированную дату
                }).eq("id", broadcast_id).execute()
                
                # Запускаем отправку (в фоне через asyncio.create_task)
                import asyncio
                asyncio.create_task(process_broadcast(broadcast_id))
    except Exception as e:
        logger.error(f"Error checking scheduled broadcasts: {e}", exc_info=True)

async def process_broadcast(broadcast_id: int):
    """Фоновая задача для отправки рассылки"""
    try:
        # Получаем данные рассылки
        broadcast_res = await supabase.table("broadcasts").select("*").eq("id", broadcast_id).single().execute()
        if not broadcast_res.data:
            logger.error(f"Broadcast {broadcast_id} not found")
            return
        
        broadcast = broadcast_res.data
        message = broadcast["message"]
        recipient_type = broadcast["recipient_type"]
        image_url = broadcast.get("image_url")

        # Обновляем статус на "sending"
        await supabase.table("broadcasts").update({"status": "sending"}).eq("id", broadcast_id).execute()
        
        # Получаем список получателей
        recipients = []
        
        if recipient_type == "all":
            # Все пользователи
            users_res = await supabase.table("users").select("tg_id").execute()
            recipients = [user["tg_id"] for user in (users_res.data or []) if user.get("tg_id")]
        
        elif recipient_type == "selected":
            # Выбранные пользователи
            recipient_ids = broadcast.get("recipient_ids", [])
            if recipient_ids:
                users_res = await supabase.table("users").select("tg_id").in_("id", recipient_ids).execute()
                recipients = [user["tg_id"] for user in (users_res.data or []) if user.get("tg_id")]
        
        elif recipient_type == "by_balance":
            # По балансу баллов
            balance_min = broadcast.get("filter_balance_min")
            balance_max = broadcast.get("filter_balance_max")
            query = supabase.table("users").select("tg_id")
            if balance_min is not None:
                query = query.gt("balance", balance_min - 1)  # >= balance_min
            if balance_max is not None:
                query = query.lt("balance", balance_max + 1)  # <= balance_max
            users_res = await query.execute()
            recipients = [user["tg_id"] for user in (users_res.data or []) if user.get("tg_id")]
        
        elif recipient_type == "by_date":
            # По дате регистрации
            date_from = broadcast.get("filter_date_from")
            date_to = broadcast.get("filter_date_to")
            query = supabase.table("users").select("tg_id")
            if date_from:
                query = query.gt("created_at", date_from)
            if date_to:
                query = query.lt("created_at", date_to)
            users_res = await query.execute()
            recipients = [user["tg_id"] for user in (users_res.data or []) if user.get("tg_id")]
        
        # Отправляем сообщения
        sent_count = 0
        failed_count = 0
        
        if not _broadcast_bot:
            logger.error("Broadcast bot not set, cannot send messages")
            await supabase.table("broadcasts").update({
                "status": "failed",
                "failed_count": len(recipients)
            }).eq("id", broadcast_id).execute()
            return
        
        for tg_id in recipients:
            try:
                success = await send_broadcast_message(_broadcast_bot, tg_id, message, image_url)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error sending broadcast to {tg_id}: {e}")
                failed_count += 1
        
        # Обновляем статус
        # Если все отправлено успешно - completed, если есть ошибки - тоже completed (но с failed_count > 0)
        status = "completed"
        await supabase.table("broadcasts").update({
            "status": status,
            "sent_count": sent_count,
            "failed_count": failed_count
        }).eq("id", broadcast_id).execute()
        
        logger.info(f"Broadcast {broadcast_id} completed: {sent_count} sent, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error processing broadcast {broadcast_id}: {e}", exc_info=True)
        try:
            await supabase.table("broadcasts").update({
                "status": "failed",
                "failed_count": 0
            }).eq("id", broadcast_id).execute()
        except:
            pass

@router.post("/broadcasts")
async def create_broadcast(data: Dict[str, Any], background_tasks: BackgroundTasks, admin_id: int = Depends(get_current_admin)):
    """Создает новую рассылку"""
    try:
        scheduled_at = data.get("scheduled_at")
        # Если указана запланированная дата, статус должен быть 'scheduled'
        status = "scheduled" if scheduled_at else "pending"
        
        broadcast_data = {
            "message": data.get("message", ""),
            "recipient_type": data.get("recipient_type", "all"),
            "recipient_ids": data.get("recipient_ids", []),
            "filter_balance_min": data.get("filter_balance_min"),
            "filter_balance_max": data.get("filter_balance_max"),
            "filter_date_from": data.get("filter_date_from"),
            "filter_date_to": data.get("filter_date_to"),
            "scheduled_at": scheduled_at,
            "status": status,
            "created_by": admin_id
        }
        
        # Добавляем image_url если указан
        image_url = data.get("image_url")
        if image_url is not None:
            broadcast_data["image_url"] = image_url
        
        try:
            res = await supabase.table("broadcasts").insert(broadcast_data).execute()
            # НЕ запускаем отправку автоматически - пользователь должен нажать "Отправить" или дождаться scheduled_at
            return res.data[0] if res.data else {}
        except Exception as insert_error:
            # Если ошибка связана с отсутствием колонки image_url, пробуем без неё
            error_str = str(insert_error)
            if "image_url" in error_str and ("PGRST204" in error_str or "column" in error_str.lower()):
                # Удаляем image_url и пробуем снова
                broadcast_data_without_image = {k: v for k, v in broadcast_data.items() if k != "image_url"}
                res = await supabase.table("broadcasts").insert(broadcast_data_without_image).execute()
                logger.warning(f"Created broadcast without image_url (column missing in DB). Please run migration 007_enhance_broadcasts.sql")
                return res.data[0] if res.data else {}
            else:
                # Другая ошибка - пробрасываем дальше
                raise
    except Exception as e:
        logger.error(f"Error in create_broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/broadcasts")
async def get_broadcasts(_: int = Depends(get_current_admin)):
    """Получает список всех рассылок"""
    try:
        res = await supabase.table("broadcasts").select("*").order("created_at", desc=True).limit(50).execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error in get_broadcasts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/broadcasts/{id}")
async def get_broadcast(id: int, _: int = Depends(get_current_admin)):
    """Получает информацию о рассылке"""
    try:
        res = await supabase.table("broadcasts").select("*").eq("id", id).single().execute()
        return res.data if res.data else {}
    except Exception as e:
        logger.error(f"Error in get_broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/broadcasts/{id}/send")
async def send_broadcast(id: int, background_tasks: BackgroundTasks, _: int = Depends(get_current_admin)):
    """Запускает отправку рассылки"""
    try:
        # Проверяем, что рассылка существует
        res = await supabase.table("broadcasts").select("*").eq("id", id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Broadcast not found")
        
        broadcast = res.data
        
        if broadcast["status"] not in ["pending", "failed", "scheduled"]:
            raise HTTPException(status_code=400, detail=f"Broadcast is already {broadcast['status']}")
        
        # Сбрасываем счетчики и статус
        await supabase.table("broadcasts").update({
            "status": "pending",
            "sent_count": 0,
            "failed_count": 0,
            "scheduled_at": None  # Убираем запланированную дату при ручной отправке
        }).eq("id", id).execute()
        
        # Запускаем отправку в фоне
        background_tasks.add_task(process_broadcast, id)
        
        return {"status": "ok", "message": "Broadcast sending started"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/broadcasts/{id}")
async def delete_broadcast(id: int, _: int = Depends(get_current_admin)):
    """Удаляет рассылку"""
    try:
        # Проверяем, что рассылка существует
        res = await supabase.table("broadcasts").select("*").eq("id", id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Broadcast not found")
        
        broadcast = res.data
        # Разрешаем удаление только для определенных статусов
        if broadcast["status"] not in ["pending", "scheduled", "failed"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete broadcast with status '{broadcast['status']}'. Only pending, scheduled, or failed broadcasts can be deleted."
            )
        
        # Удаляем рассылку
        await supabase.table("broadcasts").delete().eq("id", id).execute()
        
        return {"status": "ok", "message": "Broadcast deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- Bot Buttons ---

@router.get("/bot-buttons")
async def get_bot_buttons(_: int = Depends(get_current_admin)):
    """Получает список всех кнопок бота"""
    try:
        res = await supabase.table("bot_buttons").select("*").order("row_number").order("order_in_row").execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error in get_bot_buttons: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/bot-buttons")
async def create_bot_button(data: Dict[str, Any], _: int = Depends(get_current_admin)):
    """Создает новую кнопку"""
    try:
        res = await supabase.table("bot_buttons").insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in create_bot_button: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/bot-buttons/{id}")
async def update_bot_button(id: int, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    """Обновляет кнопку"""
    try:
        res = await supabase.table("bot_buttons").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_bot_button: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/bot-buttons/{id}")
async def delete_bot_button(id: int, _: int = Depends(get_current_admin)):
    """Удаляет кнопку"""
    try:
        await supabase.table("bot_buttons").delete().eq("id", id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in delete_bot_button: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
