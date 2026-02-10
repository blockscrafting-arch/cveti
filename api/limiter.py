"""
Rate limiter для защиты webhook и admin endpoints.
Использует in-memory хранилище (без Redis).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
