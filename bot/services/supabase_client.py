"""
Альтернативная реализация Supabase клиента через прямые HTTP запросы.
Это обходит проблему с pyroaring на Python 3.14.
Использует async везде для правильной работы с FastAPI и aiogram.
"""
import httpx
from bot.config import settings
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Глобальный async клиент (singleton)
_async_client: Optional['SupabaseClient'] = None

class SupabaseClient:
    """Async HTTP клиент для Supabase REST API"""
    
    def __init__(self):
        self.url = settings.SUPABASE_URL.rstrip('/')
        self.key = settings.SUPABASE_KEY
        self.rest_path = settings.SUPABASE_REST_PATH.strip().strip('/')
        self.headers = {
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        if self.key:
            self.headers["apikey"] = self.key
            self.headers["Authorization"] = f"Bearer {self.key}"
        self.client = httpx.AsyncClient(timeout=30.0)

    def _build_url(self, *parts: str) -> str:
        """Собирает URL для REST и RPC, учитывая опциональный префикс."""
        base = self.url
        if self.rest_path:
            base = f"{base}/{self.rest_path}"
        extra = "/".join(part.strip("/") for part in parts if part)
        return f"{base}/{extra}" if extra else base
    
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()
    
    async def _request(self, method: str, table: str, **kwargs) -> Any:
        """Базовый метод для HTTP запросов с обработкой ошибок"""
        url = self._build_url(table)
        try:
            response = await self.client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            logger.error(f"Supabase HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Supabase request error: {e}")
            raise
    
    async def rpc(self, function_name: str, params: Optional[Dict] = None) -> Any:
        """Выполнить RPC запрос (хранимую процедуру)"""
        url = self._build_url("rpc", function_name)
        try:
            response = await self.client.post(url, headers=self.headers, json=params or {})
            response.raise_for_status()
            return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            logger.error(f"Supabase RPC error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Supabase RPC request error: {e}")
            raise

    async def select(self, table: str, filters: Optional[Dict] = None, limit: Optional[int] = None, order_by: Optional[str] = None, desc: bool = False) -> List[Dict]:
        """SELECT запрос"""
        params = {}
        if filters:
            for key, value in filters.items():
                if isinstance(value, tuple):
                    op, val = value
                    if op == "in" and isinstance(val, (list, tuple)):
                        # Формат для IN: column=in.(value1,value2,value3)
                        params[f"{key}"] = f"in.({','.join(str(v) for v in val)})"
                    else:
                        # Поддержка операторов: ("eq", value), ("lt", value), ("lte", value), ("gt", value), ("gte", value)
                        params[f"{key}"] = f"{op}.{val}"
                else:
                    # Обратная совместимость: просто значение = равенство
                    params[f"{key}"] = f"eq.{value}"
        if limit:
            params["limit"] = str(limit)
        if order_by:
            params["order"] = f"{order_by}.{'desc' if desc else 'asc'}"
        
        result = await self._request("GET", table, params=params)
        return result if result else []
    
    async def select_multi_order(self, table: str, filters: Optional[Dict] = None, limit: Optional[int] = None, order_by_list: List[tuple] = None) -> List[Dict]:
        """SELECT запрос с множественной сортировкой"""
        params = {}
        if filters:
            for key, value in filters.items():
                if isinstance(value, tuple):
                    op, val = value
                    if op == "in" and isinstance(val, (list, tuple)):
                        # Формат для IN: column=in.(value1,value2,value3)
                        params[f"{key}"] = f"in.({','.join(str(v) for v in val)})"
                    else:
                        # Поддержка операторов: ("eq", value), ("lt", value), ("lte", value), ("gt", value), ("gte", value)
                        params[f"{key}"] = f"{op}.{val}"
                else:
                    # Обратная совместимость: просто значение = равенство
                    params[f"{key}"] = f"eq.{value}"
        if limit:
            params["limit"] = str(limit)
        if order_by_list:
            # Формат: order=column1.asc,column2.desc
            order_parts = [f"{col}.{'desc' if desc else 'asc'}" for col, desc in order_by_list]
            params["order"] = ",".join(order_parts)
        
        result = await self._request("GET", table, params=params)
        return result if result else []
    
    async def insert(self, table: str, data: Dict[str, Any]) -> List[Dict]:
        """INSERT запрос"""
        result = await self._request("POST", table, json=data)
        return result if result else []
    
    async def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> List[Dict]:
        """UPDATE запрос"""
        params = {}
        for key, value in filters.items():
            if isinstance(value, tuple):
                # Поддержка операторов: ("eq", value), ("lt", value), ("gt", value)
                op, val = value
                params[f"{key}"] = f"{op}.{val}"
            else:
                # Обратная совместимость: просто значение = равенство
                params[f"{key}"] = f"eq.{value}"
        
        result = await self._request("PATCH", table, params=params, json=data)
        return result if result else []
    
    async def delete(self, table: str, filters: Dict[str, Any]) -> None:
        """DELETE запрос"""
        params = {}
        for key, value in filters.items():
            if isinstance(value, tuple):
                # Поддержка операторов: ("eq", value), ("lt", value), ("gt", value)
                op, val = value
                params[f"{key}"] = f"{op}.{val}"
            else:
                # Обратная совместимость: просто значение = равенство
                params[f"{key}"] = f"eq.{value}"
        
        await self._request("DELETE", table, params=params)

def get_supabase() -> SupabaseClient:
    """Получить глобальный async клиент Supabase"""
    global _async_client
    if _async_client is None:
        _async_client = SupabaseClient()
    return _async_client

# Для обратной совместимости с кодом, который использует supabase.table()...execute()
class TableProxy:
    """Прокси для имитации supabase.table().select()...execute() с async"""
    
    def __init__(self, client: SupabaseClient, table: str):
        self.client = client
        self.table = table
        self._filters = {}
        self._order_by = []  # Список кортежей (column, desc)
        self._limit = None
        self._single = False
        self._is_insert = False
        self._is_update = False
        self._is_delete = False
        self._insert_data = None
        self._update_data = None
    
    def select(self, *args):
        """Игнорируем аргументы select, возвращаем все поля"""
        return self
    
    def eq(self, column: str, value: Any):
        """Добавить фильтр равенства"""
        self._filters[column] = ("eq", value)
        return self
    
    def lt(self, column: str, value: Any):
        """Добавить фильтр меньше чем"""
        self._filters[column] = ("lt", value)
        return self
    
    def lte(self, column: str, value: Any):
        """Добавить фильтр меньше или равно"""
        self._filters[column] = ("lte", value)
        return self
    
    def gt(self, column: str, value: Any):
        """Добавить фильтр больше чем"""
        self._filters[column] = ("gt", value)
        return self
    
    def gte(self, column: str, value: Any):
        """Добавить фильтр больше или равно"""
        self._filters[column] = ("gte", value)
        return self
    
    def in_(self, column: str, values: List[Any]):
        """Добавить фильтр IN (значение в списке)"""
        # Supabase использует формат column=in.(value1,value2)
        self._filters[column] = ("in", tuple(values))
        return self
    
    def order(self, column: str, desc: bool = False, **kwargs):
        """Добавить сортировку (поддерживает множественные вызовы)"""
        self._order_by.append((column, desc))
        return self
    
    def limit(self, count: int):
        """Ограничить количество результатов"""
        self._limit = count
        return self
    
    def single(self):
        """Получить одну запись"""
        self._single = True
        return self
    
    async def execute(self):
        """Выполнить запрос (async)"""
        if self._is_delete:
            await self.client.delete(self.table, self._filters)
            # Сбрасываем флаги
            self._is_delete = False
            self._filters = {}
            class Result:
                def __init__(self, data):
                    self.data = data if isinstance(data, list) else [data]
            return Result([])
        
        if self._is_insert:
            result = await self.client.insert(self.table, self._insert_data)
            # Сбрасываем флаги
            self._is_insert = False
            self._insert_data = None
            class Result:
                def __init__(self, data):
                    self.data = data if isinstance(data, list) else [data]
            return Result(result)
        
        if self._is_update:
            result = await self.client.update(self.table, self._filters, self._update_data)
            # Сбрасываем флаги
            self._is_update = False
            self._update_data = None
            self._filters = {}
            class Result:
                def __init__(self, data):
                    self.data = data if isinstance(data, list) else [data]
            return Result(result)
        
        # SELECT запрос
        # Если есть множественная сортировка, используем специальный метод
        if len(self._order_by) > 1:
            result = await self.client.select_multi_order(
                self.table, 
                filters=self._filters, 
                limit=self._limit,
                order_by_list=self._order_by
            )
        else:
            order_by = self._order_by[0][0] if self._order_by else None
            desc = self._order_by[0][1] if self._order_by else False
            result = await self.client.select(
                self.table, 
                filters=self._filters, 
                limit=self._limit,
                order_by=order_by,
                desc=desc
            )
        
        if self._single:
            result = result[0] if result else None
        
        # Имитируем объект с атрибутом .data
        class Result:
            def __init__(self, data):
                self.data = data
        
        return Result(result)
    
    def insert(self, data: Dict):
        """Вставить данные"""
        self._is_insert = True
        self._insert_data = data
        return self
    
    def update(self, data: Dict):
        """Обновить данные"""
        self._is_update = True
        self._update_data = data
        return self
    
    def delete(self):
        """Удалить данные"""
        self._is_delete = True
        return self

# Обертка для supabase.table()
class RPCProxy:
    """Прокси для имитации supabase.rpc().execute()"""
    def __init__(self, client: SupabaseClient, name: str, params: Optional[Dict] = None):
        self.client = client
        self.name = name
        self.params = params

    async def execute(self):
        result = await self.client.rpc(self.name, self.params)
        # Имитируем объект с атрибутом .data
        class Result:
            def __init__(self, data):
                self.data = data
        return Result(result)

class SupabaseWrapper:
    """Обертка для имитации supabase.table() API с async"""
    
    def __init__(self, client: SupabaseClient):
        self.client = client
    
    def table(self, name: str):
        return TableProxy(self.client, name)
    
    def rpc(self, name: str, params: Optional[Dict] = None):
        return RPCProxy(self.client, name, params)

# Глобальный объект для обратной совместимости (async версия)
supabase = SupabaseWrapper(get_supabase())
