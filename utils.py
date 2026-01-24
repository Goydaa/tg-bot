import re
from datetime import datetime, timedelta

def validate_email(email):
    """Проверка корректности email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """Проверка корректности телефона"""
    # Убираем все нецифровые символы кроме +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем российские номера
    if phone.startswith('+7') and len(phone) == 12:
        return True
    elif phone.startswith('8') and len(phone) == 11:
        return True
    elif phone.startswith('7') and len(phone) == 11:
        return True
    
    return False

def validate_telegram_username(username):
    """Проверка корректности Telegram username"""
    if not username:
        return False
    
    # Убираем @ если есть
    if username.startswith('@'):
        username = username[1:]
    
    # Telegram username должен быть 5-32 символа, содержать только буквы, цифры и underscore
    pattern = r'^[a-zA-Z0-9_]{5,32}$'
    return bool(re.match(pattern, username))

def validate_date(date_str):
    """Проверка корректности даты"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_time(time_str):
    """Проверка корректности времени"""
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False

def get_next_dates(days=7):
    """Генерация следующих дат для выбора"""
    dates = []
    today = datetime.now()
    for i in range(1, days + 1):
        next_date = today + timedelta(days=i)
        dates.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'display': next_date.strftime('%d.%m.%Y')
        })
    return dates

def get_time_slots():
    """Генерация временных слотов"""
    return [
        '09:00', '10:00', '11:00', '12:00',
        '13:00', '14:00', '15:00', '16:00',
        '17:00', '18:00', '19:00', '20:00'
    ]