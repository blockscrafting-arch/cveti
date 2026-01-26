import httpx
import logging
from typing import Dict, Any, Optional, List
from bot.config import settings

logger = logging.getLogger(__name__)

class YClientsAPI:
    """HTTP клиент для YClients API v1"""
    
    def __init__(self):
        self.base_url = "https://api.yclients.com/api/v1"
        self.partner_token = settings.YCLIENTS_PARTNER_TOKEN
        self.user_token = settings.YCLIENTS_USER_TOKEN
        self.company_id = settings.YCLIENTS_COMPANY_ID
        
        # Формируем Authorization header: если есть User Token, используем оба, иначе только Partner Token
        if self.user_token:
            auth_header = f"Bearer {self.partner_token}, User {self.user_token}"
        else:
            auth_header = f"Bearer {self.partner_token}"
        
        self.headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/vnd.yclients.v2+json" # Рекомендуется v2 для некоторых методов
        }
        self.client = httpx.AsyncClient(timeout=20.0)

    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()

    async def _request(self, method: str, path: str, use_user_token: bool = True, **kwargs) -> Any:
        """
        Базовый метод для запросов с обработкой ошибок
        
        Args:
            method: HTTP метод (GET, POST, etc.)
            path: Путь API (без базового URL)
            use_user_token: Использовать ли User Token в заголовке (по умолчанию True)
            **kwargs: Дополнительные параметры для httpx.request
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        
        # Формируем заголовки: для некоторых методов нужен только Partner Token
        headers = self.headers.copy()
        if not use_user_token or not self.user_token:
            headers["Authorization"] = f"Bearer {self.partner_token}"
        
        try:
            response = await self.client.request(method, url, headers=headers, **kwargs)
            
            # Логируем ошибки для отладки
            if response.status_code >= 400:
                error_text = response.text[:500] if response.text else "No error text"
                logger.error(f"YClients API error: {response.status_code} - {error_text} (URL: {url}, Method: {method})")
            
            response.raise_for_status()
            
            # Проверяем, есть ли содержимое для парсинга JSON
            if response.content:
                return response.json()
            return None
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:500] if e.response.text else "No error text"
            logger.error(f"YClients HTTP error: {e.response.status_code} for {url} - {error_text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"YClients request error: {str(e)} for {url}")
            return None
        except Exception as e:
            logger.error(f"YClients unexpected error: {str(e)} for {url}", exc_info=True)
            return None

    async def get_client_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Поиск клиента по номеру телефона в филиале"""
        # Очищаем телефон от лишних символов (нужен формат 7xxxxxxxxxx)
        clean_phone = ''.join(filter(str.isdigit, phone))
        if clean_phone.startswith('8'): clean_phone = '7' + clean_phone[1:]
        
        path = f"clients/{self.company_id}"
        params = {"phone": clean_phone}
        
        result = await self._request("GET", path, params=params)
        if result and result.get("data") and len(result["data"]) > 0:
            # Возвращаем первого найденного клиента
            return result["data"][0]
        return None

    async def get_client_loyalty_info(self, client_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о картах лояльности и балансе клиента.
        В YClients лояльность привязана к клиенту и филиалу.
        
        Пробует несколько вариантов endpoints, так как API может отличаться.
        
        Returns:
            Dict с информацией о карте лояльности или None, если карта не найдена
        """
        if not client_id:
            logger.warning("get_client_loyalty_info called with empty client_id")
            return None
        
        # Вариант 1: Получаем полную информацию о клиенте (может содержать баланс)
        try:
            client_path = f"clients/{self.company_id}/{client_id}"
            client_info = await self._request("GET", client_path, use_user_token=True)
            if client_info:
                # Проверяем, есть ли баланс в информации о клиенте
                if isinstance(client_info, dict):
                    if "balance" in client_info or "loyalty_balance" in client_info or "bonus" in client_info:
                        return client_info
                    # Может быть вложено в data
                    if "data" in client_info and isinstance(client_info["data"], dict):
                        data = client_info["data"]
                        if "balance" in data or "loyalty_balance" in data or "bonus" in data:
                            return data
        except Exception as e:
            logger.debug(f"Failed to get client info for loyalty: {e}")
        
        # Вариант 2: Пробуем получить карты лояльности через разные endpoints
        endpoints_to_try = [
            f"loyalty/client_cards/{client_id}",
            f"loyalty/client/{self.company_id}/{client_id}",
            f"loyalty/cards/{self.company_id}/{client_id}",
            f"clients/{self.company_id}/{client_id}/loyalty",
        ]
        
        for path in endpoints_to_try:
            try:
                result = await self._request("GET", path, use_user_token=True)
                
                if result:
                    # Обрабатываем разные форматы ответа API
                    if isinstance(result, list):
                        if len(result) > 0:
                            # Возвращаем информацию по первой карте (обычно одна основная)
                            return result[0]
                    elif isinstance(result, dict):
                        if "data" in result:
                            data = result["data"]
                            if isinstance(data, list) and len(data) > 0:
                                return data[0]
                            elif isinstance(data, dict):
                                return data
                        # Если сам результат - это данные карты
                        if "balance" in result or "card" in result or "points" in result:
                            return result
                    
                    logger.debug(f"Got response from {path}, but format unexpected: {type(result)}")
            except Exception as e:
                logger.debug(f"Endpoint {path} failed: {e}")
                continue
        
        logger.debug(f"No loyalty info found for client_id={client_id} in company_id={self.company_id}")
        return None

    async def get_client_loyalty_card(self, client_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает первую карту лояльности клиента (если есть)."""
        if not client_id:
            return None

        endpoints_to_try = [
            f"loyalty/client_cards/{client_id}",
            f"loyalty/client/{self.company_id}/{client_id}",
            f"loyalty/cards/{self.company_id}/{client_id}",
            f"clients/{self.company_id}/{client_id}/loyalty",
        ]
        for path in endpoints_to_try:
            try:
                result = await self._request("GET", path, use_user_token=True)
                if not result:
                    continue
                if isinstance(result, list) and result:
                    return result[0]
                if isinstance(result, dict):
                    data = result.get("data")
                    if isinstance(data, list) and data:
                        return data[0]
                    if isinstance(data, dict):
                        return data
                    if "card" in result and isinstance(result["card"], dict):
                        return result["card"]
                    if "id" in result:
                        return result
            except Exception as e:
                logger.debug(f"Failed to get loyalty cards from {path}: {e}")
        return None

    async def manual_loyalty_transaction(
        self,
        card_id: int,
        amount: float,
        operation_type: str,
        comment: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Ручная операция по карте лояльности (credit/debit/correction/refund)."""
        if not card_id:
            return None
        payload: Dict[str, Any] = {
            "amount": amount,
            "operation_type": operation_type,
        }
        if comment:
            payload["comment"] = comment
        path = f"company/{self.company_id}/loyalty/cards/{card_id}/manual_transaction"
        return await self._request("POST", path, json=payload, use_user_token=True)

    def _format_visit_status(self, raw: Dict[str, Any]) -> str:
        if raw.get("deleted") or raw.get("canceled"):
            return "Отменено"
        attendance = raw.get("attendance")
        if attendance is None:
            attendance = raw.get("visit_attendance")
        if isinstance(attendance, str) and attendance.lstrip("-").isdigit():
            attendance = int(attendance)
        if attendance == 2:
            return "Подтверждено"
        if attendance == 1:
            return "Визит состоялся"
        if attendance == 0:
            return "Ожидается"
        if attendance == -1:
            return "Не пришли"
        if raw.get("confirmed") is False:
            return "Не подтверждено"
        return "Запись"

    def _normalize_visit(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        services_titles: List[str] = []
        services_total = None
        services = raw.get("services") or []
        if isinstance(services, list):
            for service in services:
                if not isinstance(service, dict):
                    continue
                title = service.get("title") or service.get("name")
                if title:
                    services_titles.append(str(title))
                cost = service.get("cost")
                if cost is None:
                    cost = service.get("first_cost")
                if cost is None:
                    cost = service.get("manual_cost")
                amount = service.get("amount", 1)
                if cost is not None and not isinstance(cost, bool):
                    try:
                        cost_value = float(cost)
                        amount_value = float(amount) if amount is not None else 1.0
                        services_total = (services_total or 0) + cost_value * amount_value
                    except (ValueError, TypeError):
                        pass

        amount = None
        amount_candidates = [
            raw.get("amount"),
            raw.get("sum"),
            raw.get("total_cost"),
            raw.get("cost"),
            raw.get("prepaid"),
            raw.get("paid_full")
        ]
        for candidate in amount_candidates:
            if candidate is None or isinstance(candidate, bool):
                continue
            try:
                amount = float(candidate)
                if amount <= 0:
                    amount = None
                    continue
                break
            except (ValueError, TypeError):
                continue
        if amount is None and services_total is not None:
            amount = services_total

        staff = raw.get("staff") or {}
        master = None
        if isinstance(staff, dict):
            master = staff.get("name") or staff.get("title")
        if not master:
            master = raw.get("staff_name")

        visit_datetime = raw.get("datetime") or raw.get("date") or raw.get("create_date")

        return {
            "item_type": "visit",
            "visit_id": raw.get("id") or raw.get("visit_id"),
            "visit_datetime": visit_datetime,
            "services": services_titles,
            "master": master,
            "amount": amount,
            "status": self._format_visit_status(raw)
        }

    async def get_client_visits(self, client_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает историю визитов клиента и нормализует данные для UI."""
        if not client_id:
            return []

        params = {
            "client_id": client_id,
            "count": limit,
            "page": 1
        }
        result = await self._request("GET", f"records/{self.company_id}", params=params)
        if not result:
            return []

        raw_visits = []
        if isinstance(result, dict):
            raw_visits = result.get("data") or []
        elif isinstance(result, list):
            raw_visits = result

        if not isinstance(raw_visits, list):
            return []

        normalized = []
        for visit in raw_visits:
            if isinstance(visit, dict):
                normalized.append(self._normalize_visit(visit))
        return normalized

    async def get_companies_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        Получает список компаний (филиалов), доступных для партнера.
        Используется только Partner Token (без User Token).
        Полезно для поиска Company ID.
        """
        result = await self._request("GET", "companies", use_user_token=False)
        
        if result and isinstance(result, dict) and "data" in result:
            return result["data"]
        elif isinstance(result, list):
            return result
        return []

# Глобальный экземпляр сервиса
yclients = YClientsAPI()
