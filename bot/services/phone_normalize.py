"""
Нормализация и валидация номеров телефонов
"""
import re

def normalize_phone(phone: str) -> str:
    """
    Приводит номер телефона к единому стандарту +7XXXXXXXXXX
    Валидирует формат после нормализации
    """
    if not phone:
        return ""
    
    # Оставляем только цифры
    digits = "".join(filter(str.isdigit, phone))
    
    # Если начинается с 8, меняем на 7
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    
    # Если начинается без 7, добавляем 7
    if len(digits) == 10:
        digits = "7" + digits
    
    # Валидация: должен быть 11 цифр и начинаться с 7
    if len(digits) != 11 or not digits.startswith("7"):
        return ""
    
    normalized = f"+{digits}"
    
    # Финальная проверка формата
    if not re.match(r'^\+7\d{10}$', normalized):
        return ""
    
    return normalized
