from datetime import datetime, timedelta
import re

def validate_telegram_username(username):
    if not username or len(username) < 5 or len(username) > 32:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_]+$', username))

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return datetime.strptime(date_str, '%Y-%m-%d') >= datetime.now().date()
    except:
        return False

def validate_time(time_str):
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except:
        return False

def get_next_dates(days=7):
    dates = []
    for i in range(days):
        date = datetime.now() + timedelta(days=i+1)
        dates.append({
            'date': date.strftime('%Y-%m-%d'),
            'display': date.strftime('%d.%m.%Y')
        })
    return dates

def get_time_slots():
    return ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
