import argparse
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List

from bot.services.supabase_client import supabase
from bot.services.phone_normalize import normalize_phone
from bot.services.yclients_api import yclients

logger = logging.getLogger(__name__)


def _pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


async def _get_user(user_id: Optional[int], tg_id: Optional[int], phone: Optional[str]) -> Optional[Dict[str, Any]]:
    if user_id:
        res = await supabase.table("users").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None

    if tg_id:
        res = await supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        return res.data[0] if res.data else None

    if phone:
        normalized = normalize_phone(phone)
        if not normalized:
            raise ValueError("Could not normalize phone")
        res = await supabase.table("users").select("*").eq("phone", normalized).execute()
        return res.data[0] if res.data else None

    raise ValueError("Specify one of: user_id, tg_id, phone")


async def _get_transactions(user_id: int, limit: int) -> List[Dict[str, Any]]:
    res = await supabase.table("loyalty_transactions") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    return res.data if res.data else []


async def _get_webhook_logs(phone: Optional[str], limit: int) -> List[Dict[str, Any]]:
    if not phone:
        return []
    res = await supabase.table("webhook_log") \
        .select("*") \
        .eq("phone", phone) \
        .order("received_at", desc=True) \
        .limit(limit) \
        .execute()
    return res.data if res.data else []


async def _get_available_balance(user_id: int) -> Optional[int]:
    try:
        rpc_res = await supabase.rpc("get_user_available_balance", {"p_user_id": user_id}).execute()
        if isinstance(rpc_res.data, int):
            return rpc_res.data
        if isinstance(rpc_res.data, dict) and "result" in rpc_res.data:
            return rpc_res.data["result"]
    except Exception as exc:
        logger.warning("RPC get_user_available_balance failed: %s", exc)
    return None


async def _get_yclients_snapshot(user: Dict[str, Any]) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {}
    yclients_id = user.get("yclients_id")
    phone = user.get("phone")

    if not yclients_id and phone:
        client = await yclients.get_client_by_phone(phone)
        if client and client.get("id"):
            yclients_id = client["id"]
            snapshot["client_by_phone"] = client

    snapshot["yclients_id"] = yclients_id
    if not yclients_id:
        return snapshot

    snapshot["loyalty_info"] = await yclients.get_client_loyalty_info(int(yclients_id))
    snapshot["loyalty_card"] = await yclients.get_client_loyalty_card(int(yclients_id))
    snapshot["recent_visits"] = await yclients.get_client_visits(int(yclients_id), limit=10)
    return snapshot


async def run(user_id: Optional[int], tg_id: Optional[int], phone: Optional[str], limit: int, skip_yclients: bool) -> None:
    user = await _get_user(user_id, tg_id, phone)
    if not user:
        print("User not found")
        return

    print("User:")
    print(_pretty(user))

    tx = await _get_transactions(user["id"], limit=limit)
    print("\nTransactions:")
    print(_pretty(tx))

    webhook_logs = await _get_webhook_logs(user.get("phone"), limit=limit)
    print("\nWebhook logs:")
    print(_pretty(webhook_logs))

    available_balance = await _get_available_balance(user["id"])
    print("\nAvailable balance (RPC):")
    print(_pretty(available_balance))

    if not skip_yclients:
        print("\nYClients snapshot:")
        snapshot = await _get_yclients_snapshot(user)
        print(_pretty(snapshot))


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose user loyalty and visits data")
    parser.add_argument("--user-id", type=int, help="User ID in local DB")
    parser.add_argument("--tg-id", type=int, help="Telegram ID")
    parser.add_argument("--phone", type=str, help="Phone number")
    parser.add_argument("--limit", type=int, default=20, help="Limit for logs/transactions")
    parser.add_argument("--skip-yclients", action="store_true", help="Skip YClients API calls")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    asyncio.run(run(args.user_id, args.tg_id, args.phone, args.limit, args.skip_yclients))


if __name__ == "__main__":
    main()
