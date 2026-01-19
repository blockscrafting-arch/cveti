import hmac
import hashlib
import json
from urllib.parse import parse_qs
from bot.config import settings

def validate_init_data(init_data: str) -> bool:
    """
    Проверяет подпись данных от Telegram.
    Это необходимо, чтобы кто-то не подделал свой баланс баллов.
    """
    if not init_data:
        return False
        
    try:
        parsed_data = parse_qs(init_data)
        if 'hash' not in parsed_data:
            return False
            
        hash_received = parsed_data.pop('hash')[0]
        
        # Сортируем ключи в алфавитном порядке
        data_check_string = "\n".join([f"{k}={v[0]}" for k, v in sorted(parsed_data.items())])
        
        # Создаем секретный ключ на основе токена бота
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        
        # Вычисляем нашу подпись
        hash_calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(hash_calculated, hash_received)
    except Exception:
        return False

def get_user_id_from_init_data(init_data: str) -> int:
    """Извлекает Telegram ID из строки initData"""
    parsed_data = parse_qs(init_data)
    user_json = parsed_data.get('user', [None])[0]
    if user_json:
        user_data = json.loads(user_json)
        return user_data.get('id')
    return None
