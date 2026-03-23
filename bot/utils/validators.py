import re

def validate_nickname(nickname: str) -> bool:
    """Проверяет, что никнейм соответствует требованиям (3–16 символов, разрешённые символы)"""
    return bool(re.match(r'^[a-zA-Zа-яА-Я0-9_]{3,16}$', nickname))

def validate_trade_command(command: str) -> dict:
    """
    Парсит команду обмена формата:
    обмен @user ягода 10 камень 5
    Возвращает словарь с параметрами или None, если неверно
    """
    pattern = r'обмен\s+(@\w+)\s+(\w+)\s+(\d+)\s+(\w+)\s+(\d+)'
    match = re.match(pattern, command.strip())
    if not match:
        return None
    
    return {
        "target_user": match.group(1),
        "item1": match.group(2),
        "quantity1": int(match.group(3)),
        "item2": match.group(4),
        "quantity2": int(match.group(5))
    }

def validate_gift_command(command: str) -> dict:
    """
    Парсит команду подарка формата:
    /подарить @user камень 3
    """
    pattern = r'/подарить\s+(@\w+)\s+(\w+)\s+(\d+)'
    match = re.match(pattern, command.strip())
    if not match:
        return None
    return {
        "target_user": match.group(1),
        "item": match.group(2),
        "quantity": int(match.group(3))
    }
