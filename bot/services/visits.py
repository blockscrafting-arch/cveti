from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import logging

import httpx

from bot.services.supabase_client import supabase
from bot.services.phone_normalize import normalize_phone
from bot.services.yclients_api import yclients

logger = logging.getLogger(__name__)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        candidate = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            return None
    return None


def _is_sync_due(last_sync: Any, min_interval_minutes: int) -> bool:
    if not last_sync:
        return True
    parsed = _parse_datetime(last_sync)
    if not parsed:
        return True
    now = datetime.now(timezone.utc)
    return (now - parsed) > timedelta(minutes=min_interval_minutes)


async def get_user_visits(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Return cached visits from local DB."""
    res = await supabase.table("yclients_visits") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("visit_datetime", desc=True) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()

    items: List[Dict[str, Any]] = []
    for row in (res.data or []):
        amount = row.get("amount")
        if isinstance(amount, str):
            try:
                amount = float(amount)
            except ValueError:
                amount = None
        items.append({
            "visit_id": row.get("visit_id"),
            "visit_datetime": row.get("visit_datetime"),
            "services": row.get("services") or [],
            "master": row.get("master"),
            "amount": amount,
            "status": row.get("status"),
            "created_at": row.get("created_at")
        })
    return items


async def _upsert_visit(row: Dict[str, Any]) -> str:
    try:
        await supabase.table("yclients_visits").insert(row).execute()
        return "inserted"
    except httpx.HTTPStatusError as exc:
        if exc.response is not None and exc.response.status_code == 409:
            update_data = {k: v for k, v in row.items() if k not in ("visit_id", "user_id")}
            await supabase.table("yclients_visits") \
                .update(update_data) \
                .eq("visit_id", row["visit_id"]) \
                .execute()
            return "updated"
        raise


async def sync_user_visits(
    user_id: int,
    limit: int = 20,
    force: bool = False,
    min_interval_minutes: int = 30
) -> Dict[str, Any]:
    """Sync visits from YClients into local DB."""
    user_res = await supabase.table("users").select("*").eq("id", user_id).execute()
    if not user_res.data:
        return {"synced": False, "reason": "user_not_found", "visits": []}

    user = user_res.data[0]
    if not force and not _is_sync_due(user.get("visits_last_sync"), min_interval_minutes):
        return {"synced": False, "reason": "fresh", "visits": []}

    yclients_id = user.get("yclients_id")
    phone = user.get("phone")

    if not yclients_id and phone:
        normalized = normalize_phone(phone)
        if normalized:
            client = await yclients.get_client_by_phone(normalized)
            if client and client.get("id"):
                yclients_id = client["id"]
                try:
                    await supabase.table("users").update({"yclients_id": yclients_id}).eq("id", user_id).execute()
                except Exception as update_err:
                    logger.warning("Failed to update yclients_id for user %s: %s", user_id, update_err)

    if not yclients_id:
        return {"synced": False, "reason": "yclients_not_found", "visits": []}

    visits = await yclients.get_client_visits(int(yclients_id), limit=limit)
    now = datetime.now(timezone.utc).isoformat()

    stored = 0
    for visit in visits or []:
        if not isinstance(visit, dict):
            continue
        visit_id = visit.get("visit_id") or visit.get("id")
        if not visit_id:
            continue

        row = {
            "visit_id": int(visit_id),
            "user_id": user_id,
            "yclients_client_id": int(yclients_id),
            "visit_datetime": visit.get("visit_datetime"),
            "amount": visit.get("amount"),
            "status": visit.get("status"),
            "master": visit.get("master"),
            "services": visit.get("services") or [],
            "raw_payload": visit,
            "synced_at": now,
            "updated_at": now
        }

        try:
            await _upsert_visit(row)
            stored += 1
        except Exception as exc:
            logger.warning("Failed to upsert visit %s for user %s: %s", visit_id, user_id, exc)

    try:
        await supabase.table("users").update({
            "visits_last_sync": now,
            "updated_at": now
        }).eq("id", user_id).execute()
    except Exception as update_err:
        logger.warning("Failed to update visits_last_sync for user %s: %s", user_id, update_err)

    return {
        "synced": True,
        "reason": "ok",
        "visits": visits or [],
        "stored": stored,
        "yclients_id": yclients_id
    }
