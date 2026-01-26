from fastapi import APIRouter, Header, HTTPException, Depends, Query, BackgroundTasks, UploadFile, File, Form
from bot.services.auth import validate_init_data, get_user_id_from_init_data
from bot.services.supabase_client import supabase
from bot.services.notifications import send_broadcast_message
from bot.services.storage import get_storage_service
from bot.services.loyalty import apply_yclients_manual_transaction, get_user_available_balance, sync_user_with_yclients
from bot.config import settings
from typing import Optional, List, Dict, Any
from aiogram import Bot
import logging
import json
import re
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)
def _coerce_order(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

async def _normalize_orders(table_name: str, items: List[Dict[str, Any]]):
    if not items:
        return
    def _sort_key(item: Dict[str, Any]):
        order_val = _coerce_order(item.get("order"))
        if order_val is None:
            order_val = 10**12
        return (order_val, str(item.get("id")))
    sorted_items = sorted(items, key=_sort_key)
    for idx, item in enumerate(sorted_items):
        item_id = item.get("id")
        if not item_id:
            continue
        await supabase.table(table_name).update({"order": idx}).eq("id", item_id).execute()

def _extract_missing_column_from_error(error: Exception) -> Optional[str]:
    error_str = str(error)
    error_text = ""
    response = getattr(error, "response", None)
    if response is not None:
        try:
            error_text = response.text or ""
        except Exception:
            error_text = ""
    if error_text:
        try:
            parsed = json.loads(error_text)
            if isinstance(parsed, dict) and "message" in parsed:
                error_text = parsed.get("message") or error_text
        except Exception:
            pass
    match = re.search(r"Could not find the '([^']+)' column", error_text or error_str)
    return match.group(1) if match else None

async def _safe_broadcast_update(broadcast_id: str, update_data: Dict[str, Any]):
    pending_data = dict(update_data)
    for _ in range(6):
        if not pending_data:
            return
        try:
            await supabase.table("broadcasts").update(pending_data).eq("id", broadcast_id).execute()
            return
        except Exception as update_error:
            missing_col = _extract_missing_column_from_error(update_error)
            if missing_col and missing_col in pending_data:
                pending_data.pop(missing_col, None)
                continue
            raise

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
        # Читаем содержимое файла
        file_content = await file.read()

        # Проверяем тип файла
        allowed_exts = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif", "avif"}
        filename = file.filename or "image"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        def _detect_image_ext(content: bytes) -> Optional[str]:
            if not content or len(content) < 12:
                return None
            if content.startswith(b"\xFF\xD8\xFF"):
                return "jpg"
            if content.startswith(b"\x89PNG\r\n\x1a\n"):
                return "png"
            if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
                return "gif"
            if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
                return "webp"
            if content[4:8] == b"ftyp":
                brand = content[8:12]
                if brand in {b"heic", b"heif", b"hevc", b"hevx", b"mif1", b"msf1"}:
                    return "heic"
                if brand == b"avif":
                    return "avif"
            return None

        detected_ext = _detect_image_ext(file_content)
        is_image_type = bool(file.content_type and file.content_type.startswith("image/"))
        is_allowed_ext = ext in allowed_exts
        is_allowed_detected = detected_ext in allowed_exts if detected_ext else False

        if not is_image_type and not is_allowed_ext and not is_allowed_detected:
            detail = "Only image files are allowed"
            if file.content_type:
                detail = f"Only image files are allowed (content_type: {file.content_type}, ext: {ext or 'none'})"
            raise HTTPException(status_code=400, detail=detail)

        # Если расширение отсутствует/неподходящее, пытаемся подставить по сигнатуре
        if (not is_allowed_ext) and is_allowed_detected:
            base_name = filename.rsplit(".", 1)[0] if "." in filename else (filename or "image")
            filename = f"{base_name}.{detected_ext}"
        
        # Проверяем размер файла (максимум 50MB)
        max_size_mb = 50
        max_size = max_size_mb * 1024 * 1024
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail=f"File size exceeds {max_size_mb}MB limit")
        
        # Загружаем в Supabase Storage
        storage_service = get_storage_service()
        public_url = await storage_service.upload_file(
            file_content=file_content,
            filename=filename,
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
async def update_master(id: str, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("masters").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/masters/{id}")
async def delete_master(id: str, _: int = Depends(get_current_admin)):
    try:
        await supabase.table("masters").delete().eq("id", id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in delete_master: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/masters/{id}/move")
async def move_master(id: str, direction: str = Query(..., pattern="^(up|down)$"), _: int = Depends(get_current_admin)):
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
        all_items = all_res.data or []
        valid_items = [item for item in all_items if item.get("order") is not None]

        orders = [_coerce_order(item.get("order")) for item in all_items]
        unique_orders = len(set([o for o in orders if o is not None]))
        normalized_orders = False
        if len(all_items) > 1 and unique_orders <= 1:
            await _normalize_orders("masters", all_items)
            normalized_orders = True
            current_res = await supabase.table("masters").select("*").eq("id", id).single().execute()
            current_order = current_res.data.get("order") if current_res.data else None
            all_res = await supabase.table("masters").select("*").execute()
            all_items = all_res.data or []
            valid_items = [item for item in all_items if item.get("order") is not None]
        # Определяем направление и новый порядок
        # "up" = переместить выше в списке = уменьшить свой order = найти соседа с МЕНЬШИМ order
        # "down" = переместить ниже в списке = увеличить свой order = найти соседа с БОЛЬШИМ order
        candidates = []
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
        await supabase.table("masters").select("id,order").in_("id", [id, target["id"]]).execute()

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
async def update_service(id: str, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("services").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/services/{id}")
async def delete_service(id: str, _: int = Depends(get_current_admin)):
    try:
        await supabase.table("services").delete().eq("id", id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in delete_service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/services/{id}/move")
async def move_service(id: str, direction: str = Query(..., pattern="^(up|down)$"), _: int = Depends(get_current_admin)):
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
        all_items = all_res.data or []
        valid_items = [item for item in all_items if item.get("order") is not None]

        orders = [_coerce_order(item.get("order")) for item in all_items]
        unique_orders = len(set([o for o in orders if o is not None]))
        normalized_orders = False
        if len(all_items) > 1 and unique_orders <= 1:
            await _normalize_orders("services", all_items)
            normalized_orders = True
            current_res = await supabase.table("services").select("*").eq("id", id).single().execute()
            current_order = current_res.data.get("order") if current_res.data else None
            all_res = await supabase.table("services").select("*").execute()
            all_items = all_res.data or []
            valid_items = [item for item in all_items if item.get("order") is not None]
        # "up" = переместить выше = уменьшить свой order = найти соседа с МЕНЬШИМ order
        # "down" = переместить ниже = увеличить свой order = найти соседа с БОЛЬШИМ order
        candidates = []
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
async def update_promotion(id: str, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("promotions").update(data).eq("id", id).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error in update_promotion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/promotions/{id}")
async def delete_promotion(id: str, _: int = Depends(get_current_admin)):
    try:
        await supabase.table("promotions").delete().eq("id", id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in delete_promotion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/promotions/{id}/move")
async def move_promotion(id: str, direction: str = Query(..., pattern="^(up|down)$"), _: int = Depends(get_current_admin)):
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
async def get_user(id: str, _: int = Depends(get_current_admin)):
    try:
        res = await supabase.table("users").select("*").eq("id", id).single().execute()
        return res.data if res.data else {}
    except Exception as e:
        logger.error(f"Error in get_user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/users/{id}")
async def update_user(id: str, data: Dict[str, Any], _: int = Depends(get_current_admin)):
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
async def get_user_transactions(user_id: str, _: int = Depends(get_current_admin)):
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
async def create_transaction(user_id: str, data: Dict[str, Any], _: int = Depends(get_current_admin)):
    """Создает транзакцию и обновляет баланс пользователя"""
    try:
        # Проверяем пользователя
        user_res = await supabase.table("users").select("id").eq("id", user_id).single().execute()
        if not user_res.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        try:
            amount = int(data.get("amount", 0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid amount")
        
        if amount == 0:
            raise HTTPException(status_code=400, detail="Amount cannot be zero")
        
        description = data.get("description", "Ручное изменение баланса")
        
        # Для списаний проверяем доступный баланс
        if amount < 0:
            await sync_user_with_yclients(int(user_id))
            available_balance = await get_user_available_balance(int(user_id))
            if abs(amount) > available_balance:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недостаточно баллов. Доступно: {available_balance}"
                )

        success, message, new_balance = await apply_yclients_manual_transaction(
            user_id=int(user_id),
            amount=amount,
            description=description
        )
        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"success": True, "new_balance": new_balance}
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
                await _safe_broadcast_update(str(broadcast_id), {
                    "status": "pending",
                    "scheduled_at": None  # Убираем запланированную дату
                })
                
                # Запускаем отправку (в фоне через asyncio.create_task)
                import asyncio
                asyncio.create_task(process_broadcast(broadcast_id))
    except Exception as e:
        logger.error(f"Error checking scheduled broadcasts: {e}", exc_info=True)

async def process_broadcast(broadcast_id: str):
    """Фоновая задача для отправки рассылки"""
    try:
        # Получаем данные рассылки
        broadcast_res = await supabase.table("broadcasts").select("*").eq("id", broadcast_id).single().execute()
        if not broadcast_res.data:
            logger.error(f"Broadcast {broadcast_id} not found")
            return
        
        broadcast = broadcast_res.data or {}
        message = broadcast.get("message") or broadcast.get("content") or broadcast.get("title") or ""
        recipient_type = broadcast.get("recipient_type", "all")
        image_url = broadcast.get("image_url")

        # Обновляем статус на "sending"
        try:
            await _safe_broadcast_update(str(broadcast_id), {"status": "sending"})
        except Exception as e:
            logger.warning(f"Could not set broadcast {broadcast_id} status to 'sending': {e}")
        
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
        await _safe_broadcast_update(str(broadcast_id), {
            "status": status,
            "sent_count": sent_count,
            "failed_count": failed_count
        })
        
        logger.info(f"Broadcast {broadcast_id} completed: {sent_count} sent, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error processing broadcast {broadcast_id}: {e}", exc_info=True)
        try:
            await _safe_broadcast_update(str(broadcast_id), {
                "status": "failed",
                "failed_count": 0
            })
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
        title = data.get("title")
        if not title:
            message = data.get("message", "")
            if isinstance(message, str):
                title = message.strip()[:120]
            else:
                title = ""
        broadcast_data["title"] = title or "Рассылка"
        content = data.get("content")
        if not content:
            message = data.get("message", "")
            if isinstance(message, str):
                content = message.strip()
            else:
                content = ""
        broadcast_data["content"] = content or broadcast_data["title"]
        
        # Добавляем image_url если указан
        image_url = data.get("image_url")
        if image_url is not None:
            broadcast_data["image_url"] = image_url
        
        def _extract_missing_column(error_str: str) -> Optional[str]:
            match = re.search(r"Could not find the '([^']+)' column", error_str)
            return match.group(1) if match else None

        pending_data = dict(broadcast_data)
        last_error = None
        for _ in range(6):
            try:
                res = await supabase.table("broadcasts").insert(pending_data).execute()
                # НЕ запускаем отправку автоматически - пользователь должен нажать "Отправить" или дождаться scheduled_at
                return res.data[0] if res.data else {}
            except Exception as insert_error:
                last_error = insert_error
                error_str = str(insert_error)
                error_text = ""
                response = getattr(insert_error, "response", None)
                if response is not None:
                    try:
                        error_text = response.text or ""
                    except Exception:
                        error_text = ""
                if error_text:
                    try:
                        parsed = json.loads(error_text)
                        if isinstance(parsed, dict) and "message" in parsed:
                            error_text = parsed.get("message") or error_text
                    except Exception:
                        pass
                missing_col = _extract_missing_column(error_text or error_str)
                if missing_col and missing_col in pending_data:
                    pending_data.pop(missing_col, None)
                    continue
                raise
        if last_error:
            raise last_error
    except Exception as e:
        logger.error(f"Error in create_broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/broadcasts")
async def get_broadcasts(_: int = Depends(get_current_admin)):
    """Получает список всех рассылок"""
    try:
        res = await supabase.table("broadcasts").select("*").order("created_at", desc=True).limit(50).execute()
        items = res.data if res.data else []
        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get("message"):
                item["message"] = item.get("content") or item.get("title") or ""
        return items
    except Exception as e:
        logger.error(f"Error in get_broadcasts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/broadcasts/{id}")
async def get_broadcast(id: str, _: int = Depends(get_current_admin)):
    """Получает информацию о рассылке"""
    try:
        res = await supabase.table("broadcasts").select("*").eq("id", id).single().execute()
        data = res.data if res.data else {}
        if isinstance(data, dict) and not data.get("message"):
            data["message"] = data.get("content") or data.get("title") or ""
        return data
    except Exception as e:
        logger.error(f"Error in get_broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/broadcasts/{id}/send")
async def send_broadcast(id: str, background_tasks: BackgroundTasks, _: int = Depends(get_current_admin)):
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
        await _safe_broadcast_update(str(id), {
            "status": "pending",
            "sent_count": 0,
            "failed_count": 0,
            "scheduled_at": None  # Убираем запланированную дату при ручной отправке
        })
        
        # Запускаем отправку в фоне
        background_tasks.add_task(process_broadcast, id)
        
        return {"status": "ok", "message": "Broadcast sending started"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/broadcasts/{id}")
async def delete_broadcast(id: str, _: int = Depends(get_current_admin)):
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

@router.post("/bot-buttons/reorder")
async def reorder_bot_buttons(payload: Dict[str, Any], _: int = Depends(get_current_admin)):
    """Сохраняет порядок кнопок по строкам"""
    try:
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items:
            raise HTTPException(status_code=400, detail="Items list is required")

        grouped: Dict[int, list] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            button_id = item.get("id")
            row_number = item.get("row_number")
            order_in_row = item.get("order_in_row")
            if button_id is None or row_number is None or order_in_row is None:
                continue
            try:
                row_number = int(row_number)
                order_in_row = int(order_in_row)
            except (TypeError, ValueError):
                continue
            grouped.setdefault(row_number, []).append((order_in_row, button_id))

        if not grouped:
            raise HTTPException(status_code=400, detail="No valid items to reorder")

        normalized = []
        for row_number, row_items in grouped.items():
            row_items.sort(key=lambda x: x[0])
            for index, (_, button_id) in enumerate(row_items):
                normalized.append({
                    "id": button_id,
                    "row_number": row_number,
                    "order_in_row": index
                })

        for item in normalized:
            await supabase.table("bot_buttons").update({
                "row_number": item["row_number"],
                "order_in_row": item["order_in_row"]
            }).eq("id", item["id"]).execute()

        return {"status": "ok", "updated": len(normalized)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reorder_bot_buttons: {e}", exc_info=True)
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
