import argparse
import asyncio
import logging
from typing import List, Dict, Any, Optional

from bot.services.supabase_client import supabase
from bot.services.visits import sync_user_visits

logger = logging.getLogger(__name__)


async def _get_users(active_only: bool) -> List[Dict[str, Any]]:
    query = supabase.table("users").select("id")
    if active_only:
        query = query.eq("active", True)
    res = await query.execute()
    return res.data if res.data else []


async def run(only_user_id: Optional[int], limit_per_user: int, active_only: bool, sleep_s: float) -> None:
    if only_user_id:
        users = [{"id": only_user_id}]
    else:
        users = await _get_users(active_only=active_only)

    if not users:
        print("No users found")
        return

    logger.info("Backfilling visits for %s users", len(users))
    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue
        try:
            result = await sync_user_visits(user_id, limit=limit_per_user, force=True)
            logger.info("User %s synced: %s", user_id, result.get("reason"))
        except Exception as exc:
            logger.error("Failed to sync user %s: %s", user_id, exc)
        if sleep_s > 0:
            await asyncio.sleep(sleep_s)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill YClients visits into local DB")
    parser.add_argument("--only-user-id", type=int, help="Sync only one user id")
    parser.add_argument("--limit-per-user", type=int, default=50, help="Visits per user to fetch")
    parser.add_argument("--include-inactive", action="store_true", help="Include inactive users")
    parser.add_argument("--sleep", type=float, default=0.5, help="Delay between users (seconds)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    asyncio.run(run(args.only_user_id, args.limit_per_user, not args.include_inactive, args.sleep))


if __name__ == "__main__":
    main()
