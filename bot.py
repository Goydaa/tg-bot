import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import os
from dotenv import load_dotenv

from database import Database
from utils import validate_email, validate_phone, validate_telegram_username, validate_date, validate_time, get_next_dates, get_time_slots

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

class ApplicationStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_contact_type = State()
    waiting_for_contact = State()
    waiting_for_message = State()
    waiting_for_date = State()
    waiting_for_time = State()

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Запись на занятие")],
            [KeyboardButton(text="❓ Вопрос по курсу")],
            [KeyboardButton(text="📋 Прочее")],
            [KeyboardButton(text="📊 Статистика")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_contact_type_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📧 Email")],
            [KeyboardButton(text="📞 Телефон")],
            [KeyboardButton(text="👤 Telegram")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_date_keyboard():
    dates = get_next_dates(7)
    rows = []
    
    row = []
    for i, date_info in enumerate(dates):
        row.append(KeyboardButton(text=date_info['display']))
        if len(row) == 2 or i == len(dates) - 1:
            rows.append(row)
            row = []
    
    rows.append([KeyboardButton(text="❌ Без даты")])
    
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def get_time_keyboard():
    times = get_time_slots()
    rows = []
    
    row = []
    for i, time in enumerate(times):
        row.append(KeyboardButton(text=time))
        if len(row) == 3 or i == len(times) - 1:
            rows.append(row)
            row = []
    
    rows.append([KeyboardButton(text="❌ Без времени")])
    
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def get_admin_applications_keyboard(app_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Обработано", callback_data=f"process_{app_id}"),
            InlineKeyboardButton(text="📝 Подробнее", callback_data=f"details_{app_id}")
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{app_id}"),
            InlineKeyboardButton(text="📞 Написать", callback_data=f"message_{app_id}")
        ]
    ])

def get_admin_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Новые заявки", callback_data="admin_new")],
        [InlineKeyboardButton(text="📊 Все заявки", callback_data="admin_all")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔍 Поиск заявки", callback_data="admin_search")],
        [InlineKeyboardButton(text="⏰ Проверить напоминания", callback_data="admin_check_reminders")]
    ])

def format_application_short(app):
    app_id, user_id, username, full_name, contact_type, contact_data, app_type, message_text, appointment_date, appointment_time, created_at, status = app
    
    text = f"🆔 #{app_id} | {full_name} | {app_type.upper()}\n"
    
    if appointment_date:
        date_display = datetime.strptime(appointment_date, '%Y-%m-%d').strftime('%d.%m.%Y')
        text += f"📅 {date_display}"
        if appointment_time:
            text += f" ⏰ {appointment_time}\n"
        else:
            text += "\n"
    
    text += f"💬 {message_text[:50]}..."
    
    return text

def format_application_detailed(app):
    app_id, user_id, username, full_name, contact_type, contact_data, app_type, message_text, appointment_date, appointment_time, created_at, status = app
    
    text = f"📋 ЗАЯВКА #{app_id}\n\n"
    text += f"👤 Имя: {full_name}\n"
    text += f"👤 TG username: @{username if username else 'не указан'}\n"
    text += f"🆔 TG ID: {user_id}\n"
    text += f"📱 Контакт ({contact_type}): {contact_data}\n"
    text += f"📋 Тип: {app_type}\n"
    
    if appointment_date:
        date_display = datetime.strptime(appointment_date, '%Y-%m-%d').strftime('%d.%m.%Y')
        text += f"📅 Дата: {date_display}\n"
        if appointment_time:
            text += f"⏰ Время: {appointment_time}\n"
    
    text += f"💬 Сообщение:\n{message_text}\n\n"
    text += f"📅 Создана: {created_at}\n"
    text += f"📊 Статус: {status}\n"
    
    return text

def send_applications_summary(message, applications):
    new_apps = []
    processed_apps = []
    
    for app in applications:
        if app[11] == 'new':
            new_apps.append(app)
        else:
            processed_apps.append(app)
    
    text = "📋 ВСЕ ЗАЯВКИ\n\n"
    
    if new_apps:
        text += f"🆕 НОВЫЕ ({len(new_apps)}):\n"
        for i, app in enumerate(new_apps[:5], 1):
            app_text = format_application_short(app)
            text += f"{i}. {app_text}\n"
        
        if len(new_apps) > 5:
            text += f"... и еще {len(new_apps) - 5} новых заявок\n"
    
    if processed_apps:
        text += f"\n✅ ОБРАБОТАННЫЕ ({len(processed_apps)}):\n"
        for i, app in enumerate(processed_apps[:5], 1):
            app_text = format_application_short(app)
            text += f"{i}. {app_text}\n"
        
        if len(processed_apps) > 5:
            text += f"... и еще {len(processed_apps) - 5} обработанных заявок\n"
    
    text += f"\n📊 Итого: {len(new_apps)} новых, {len(processed_apps)} обработанных"
    
    return text

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в КлассОнлайн!\n\n"
        "Я помогу вам:\n"
        "• Записаться на занятия\n"
        "• Получить ответы на вопросы по курсам\n"
        "• Решить другие вопросы\n\n"
        "Выберите тип обращения:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📚 Список доступных команд:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/stats - Показать статистику заявок\n"
        "/cancel - Отменить текущее действие\n"
    )
    
    if message.from_user.id == ADMIN_ID:
        help_text += (
            "\n👨‍💼 Команды администратора:\n"
            "/admin - Панель администратора\n"
            "/applications - Новые заявки\n"
            "/view_all - Все заявки\n"
            "/stats_full - Полная статистика\n"
            "/search [ID] - Найти заявку по ID\n"
            "/check_reminders - Проверить напоминания\n"
        )
    
    await message.answer(help_text)

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    stats = db.get_stats()
    await message.answer(
        f"📊 Статистика заявки:\n\n"
        f"Всего заявок: {stats['total']}\n"
        f"Новых: {stats['new']}\n"
        f"Обработано: {stats['processed']}"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "👨‍💼 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_main_keyboard()
        )
    else:
        await message.answer("⛔ У вас нет доступа к админ-панели")

@dp.message(Command("check_reminders"))
async def cmd_check_reminders(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещен")
        return
    
    reminders = db.get_due_reminders()
    
    if reminders:
        text = "⏰ НАПОМИНАНИЯ ДЛЯ ОТПРАВКИ:\n\n"
        for i, reminder in enumerate(reminders[:10], 1):
            app_id, reminder_id, user_id, username = reminder[0], reminder[1], reminder[2], reminder[3]
            application = db.get_application_by_id(app_id)
            
            if application:
                date_display = datetime.strptime(application[8], '%Y-%m-%d').strftime('%d.%m.%Y')
                text += f"{i}. Заявка #{app_id} | 👤 {application[3]} | 📅 {date_display}\n"
        
        if len(reminders) > 10:
            text += f"\n... и еще {len(reminders) - 10} напоминаний"
        
        text += f"\n\nВсего: {len(reminders)} напоминаний"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить все напоминания", callback_data="admin_send_all_reminders")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("✅ Нет напоминаний для отправки")

@dp.message(Command("applications"))
async def cmd_applications(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещен")
        return
    
    applications = db.get_applications('new')
    
    if not applications:
        await message.answer("📭 Нет новых заявок")
        return
    
    await message.answer(f"📋 Найдено новых заявок: {len(applications)}")
    
    for app in applications[:10]:
        app_text = format_application_short(app)
        keyboard = get_admin_applications_keyboard(app[0])
        await message.answer(app_text, reply_markup=keyboard)

@dp.message(Command("view_all"))
async def cmd_view_all(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещен")
        return
    
    applications = db.get_all_applications()
    
    if not applications:
        await message.answer("📭 Нет заявок в базе данных")
        return
    
    await message.answer(send_applications_summary(message, applications))

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещен")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /search [ID_заявки]")
        return
    
    try:
        app_id = int(args[1])
        application = db.get_application_by_id(app_id)
        
        if application:
            app_text = format_application_detailed(application)
            keyboard = get_admin_applications_keyboard(app_id)
            await message.answer(app_text, reply_markup=keyboard)
        else:
            await message.answer(f"❌ Заявка с ID {app_id} не найдена")
    except ValueError:
        await message.answer("❌ Неверный формат ID. Используйте число.")

@dp.message(Command("stats_full"))
async def cmd_stats_full(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    stats = db.get_stats()
    applications = db.get_all_applications()
    
    type_stats = {}
    date_stats = {}
    
    for app in applications:
        app_type = app[6]
        date = app[8]
        
        type_stats[app_type] = type_stats.get(app_type, 0) + 1
        if date:
            date_stats[date] = date_stats.get(date, 0) + 1
    
    stats_text = "📊 ПОЛНАЯ СТАТИСТИКА\n\n"
    stats_text += f"Всего заявок: {stats['total']}\n"
    stats_text += f"Новых: {stats['new']}\n"
    stats_text += f"Обработано: {stats['processed']}\n\n"
    
    if type_stats:
        stats_text += "📝 По типам:\n"
        for app_type, count in type_stats.items():
            stats_text += f"• {app_type}: {count}\n"
    
    if date_stats:
        stats_text += "\n📅 Ближайшие встречи:\n"
        sorted_dates = sorted(date_stats.items())[:5]
        for date, count in sorted_dates:
            stats_text += f"• {date}: {count} встреч\n"
    
    await message.answer(stats_text)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено. Выберите тип обращения:",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text.in_(["📝 Запись на занятие", "❓ Вопрос по курсу", "📋 Прочее"]))
async def process_application_type(message: types.Message, state: FSMContext):
    app_type = {
        "📝 Запись на занятие": "запись",
        "❓ Вопрос по курсу": "вопрос",
        "📋 Прочее": "прочее"
    }[message.text]
    
    await state.update_data(application_type=app_type)
    await state.set_state(ApplicationStates.waiting_for_name)
    
    await message.answer(
        "👤 Пожалуйста, введите ваше полное имя:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(ApplicationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    await state.update_data(full_name=message.text)
    await state.set_state(ApplicationStates.waiting_for_contact_type)
    
    await message.answer(
        "📱 Выберите предпочтительный способ связи:",
        reply_markup=get_contact_type_keyboard()
    )

@dp.message(ApplicationStates.waiting_for_contact_type)
async def process_contact_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    contact_type_map = {
        "📧 Email": "email",
        "📞 Телефон": "phone",
        "👤 Telegram": "telegram"
    }
    
    if message.text not in contact_type_map:
        await message.answer("Пожалуйста, выберите способ связи из предложенных:", reply_markup=get_contact_type_keyboard())
        return
    
    contact_type = contact_type_map[message.text]
    await state.update_data(contact_type=contact_type)
    await state.set_state(ApplicationStates.waiting_for_contact)
    
    prompt_text = {
        "email": "📧 Введите ваш email адрес (например: user@example.com):",
        "phone": "📞 Введите ваш номер телефона (например: +79991234567):",
        "telegram": "👤 Введите ваш Telegram username (например: @username или просто username):"
    }[contact_type]
    
    await message.answer(prompt_text, reply_markup=get_cancel_keyboard())

@dp.message(ApplicationStates.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    data = await state.get_data()
    contact_type = data['contact_type']
    contact_data = message.text
    
    is_valid = False
    if contact_type == "email":
        is_valid = validate_email(contact_data)
        error_msg = "❌ Некорректный email адрес. Пожалуйста, введите правильный email (например: user@example.com):"
    elif contact_type == "phone":
        is_valid = validate_phone(contact_data)
        error_msg = "❌ Некорректный номер телефона. Пожалуйста, введите правильный номер (например: +79991234567):"
    else:
        if contact_data.startswith('@'):
            contact_data = contact_data[1:]
        is_valid = validate_telegram_username(contact_data)
        error_msg = "❌ Некорректный Telegram username. Пожалуйста, введите правильный username (5-32 символа, только буквы, цифры и _):"
    
    if not is_valid:
        await message.answer(error_msg, reply_markup=get_cancel_keyboard())
        return
    
    if contact_type == 'telegram' and contact_data.startswith('@'):
        contact_data = contact_data[1:]
    
    await state.update_data(contact_data=contact_data)
    
    if data['application_type'] == 'запись':
        await state.set_state(ApplicationStates.waiting_for_date)
        
        dates = get_next_dates(7)
        dates_text = "📅 Выберите предпочтительную дату из списка ниже:\n\n"
        for date_info in dates:
            dates_text += f"• {date_info['display']}\n"
        dates_text += "\nИли нажмите ❌ Без даты"
        
        await message.answer(dates_text, reply_markup=get_date_keyboard())
    else:
        await state.set_state(ApplicationStates.waiting_for_message)
        await message.answer(
            "💬 Пожалуйста, опишите ваш вопрос или пожелание:",
            reply_markup=get_cancel_keyboard()
        )

@dp.message(ApplicationStates.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    if message.text == "❌ Без даты":
        await state.update_data(appointment_date=None)
        await state.set_state(ApplicationStates.waiting_for_message)
        await message.answer(
            "💬 Пожалуйста, опишите вашу заявку или вопрос:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    try:
        date_obj = datetime.strptime(message.text, '%d.%m.%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        
        if not validate_date(formatted_date):
            raise ValueError
        
        await state.update_data(appointment_date=formatted_date)
        await state.set_state(ApplicationStates.waiting_for_time)
        
        times = get_time_slots()
        times_text = "⏰ Выберите предпочтительное время из списка ниже:\n\n"
        for time in times:
            times_text += f"• {time}\n"
        times_text += "\nИли нажмите ❌ Без времени"
        
        await message.answer(times_text, reply_markup=get_time_keyboard())
    except ValueError:
        await message.answer("❌ Некорректная дата. Пожалуйста, выберите дату из списка:", reply_markup=get_date_keyboard())

@dp.message(ApplicationStates.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    if message.text == "❌ Без времени":
        await state.update_data(appointment_time=None)
    else:
        if not validate_time(message.text):
            await message.answer("❌ Некорректное время. Пожалуйста, выберите время из списка:", reply_markup=get_time_keyboard())
            return
        await state.update_data(appointment_time=message.text)
    
    await state.set_state(ApplicationStates.waiting_for_message)
    await message.answer(
        "💬 Пожалуйста, опишите вашу заявку или вопрос:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(ApplicationStates.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    user_data = await state.get_data()
    
    app_id = db.add_application(
        user_id=message.from_user.id,
        username=message.from_user.username or "не указан",
        full_name=user_data['full_name'],
        contact_type=user_data['contact_type'],
        contact_data=user_data['contact_data'],
        app_type=user_data['application_type'],
        message=message.text,
        appointment_date=user_data.get('appointment_date'),
        appointment_time=user_data.get('appointment_time')
    )
    
    await notify_admin(app_id, user_data, message.text)
    
    confirmation_text = (
        "✅ Ваша заявка принята!\n\n"
        f"📝 Тип: {user_data['application_type']}\n"
        f"👤 Имя: {user_data['full_name']}\n"
        f"📱 Контакт: {user_data['contact_data']}\n"
    )
    
    if user_data.get('appointment_date'):
        date_display = datetime.strptime(user_data['appointment_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        confirmation_text += f"📅 Дата: {date_display}\n"
        if user_data.get('appointment_time'):
            confirmation_text += f"⏰ Время: {user_data['appointment_time']}\n"
    
    confirmation_text += "\nМы свяжемся с вами в ближайшее время!"
    
    await message.answer(confirmation_text, reply_markup=get_main_keyboard())
    
    if user_data.get('appointment_date'):
        reminder_date = datetime.strptime(user_data['appointment_date'], '%Y-%m-%d')
        reminder_date = reminder_date.replace(day=reminder_date.day - 1)
        db.add_reminder(app_id, reminder_date.strftime('%Y-%m-%d'))
        print(f"✅ Добавлено напоминание для заявки #{app_id} на {reminder_date}")
    
    await state.clear()

async def notify_admin(app_id, user_data, message_text):
    try:
        admin_text = "📝 НОВАЯ ЗАЯВКА!\n\n"
        
        if user_data.get('appointment_date'):
            date_display = datetime.strptime(user_data['appointment_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            admin_text += f"📅 ВСТРЕЧА:\n\n"
            admin_text += f"🆔 {app_id}\n"
            admin_text += f"👤 {user_data['full_name']}\n"
            admin_text += f"📅 {date_display}"
            if user_data.get('appointment_time'):
                admin_text += f" ⏰ {user_data['appointment_time']}\n"
            else:
                admin_text += "\n"
            
            contact_display = f"@{user_data['contact_data']}" if user_data['contact_type'] == 'telegram' else user_data['contact_data']
            admin_text += f"📞 {contact_display}\n\n"
        else:
            admin_text += f"🆔 ID: {app_id}\n"
            admin_text += f"👤 Имя: {user_data['full_name']}\n"
        
        admin_text += f"📋 Тип: {user_data['application_type']}\n"
        admin_text += f"💬 Сообщение: {message_text[:100]}...\n\n"
        admin_text += f"👤 ID пользователя Telegram: {user_data.get('user_id', 'не указан')}"
        
        keyboard = get_admin_applications_keyboard(app_id)
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления админу: {e}")

@dp.message(F.text == "📊 Статистика")
async def show_stats_button(message: types.Message):
    await cmd_stats(message)

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    action = callback.data
    
    if action == "admin_new":
        applications = db.get_applications('new')
        if applications:
            await callback.message.answer(f"📋 Найдено новых заявок: {len(applications)}")
            for app in applications[:5]:
                app_text = format_application_short(app)
                keyboard = get_admin_applications_keyboard(app[0])
                await callback.message.answer(app_text, reply_markup=keyboard)
        else:
            await callback.message.answer("📭 Нет новых заявок")
    
    elif action == "admin_all":
        applications = db.get_all_applications()
        if applications:
            text = send_applications_summary(callback.message, applications)
            await callback.message.answer(text)
        else:
            await callback.message.answer("📭 Нет заявок")
    
    elif action == "admin_stats":
        stats = db.get_stats()
        await callback.message.answer(
            f"📊 Статистика:\n\n"
            f"Всего заявок: {stats['total']}\n"
            f"Новых: {stats['new']}\n"
            f"Обработано: {stats['processed']}"
        )
    
    elif action == "admin_search":
        await callback.message.answer("Введите ID заявки для поиска:\nПример: /search 123")
    
    elif action == "admin_check_reminders":
        await cmd_check_reminders(callback.message)
    
    elif action == "admin_send_all_reminders":
        reminders = db.get_due_reminders()
        if reminders:
            sent_count = 0
            for reminder in reminders:
                app_id, reminder_id, user_id, username = reminder[0], reminder[1], reminder[2], reminder[3]
                
                application = db.get_application_by_id(app_id)
                if application:
                    date_display = datetime.strptime(application[8], '%Y-%m-%d').strftime('%d.%m.%Y')
                    reminder_text = f"🔔 НАПОМИНАНИЕ!\n\nУ вас запланирована встреча завтра ({date_display})"
                    
                    if application[9]:
                        reminder_text += f" в {application[9]}"
                    
                    reminder_text += "\n\nНе забудьте подготовиться!"
                    
                    try:
                        await bot.send_message(user_id, reminder_text)
                        db.mark_reminder_sent(reminder_id)
                        sent_count += 1
                    except Exception as e:
                        print(f"❌ Ошибка отправки напоминания пользователю {user_id}: {e}")
            
            await callback.message.answer(f"✅ Отправлено {sent_count} напоминаний из {len(reminders)}")
        else:
            await callback.message.answer("✅ Нет напоминаний для отправки")
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("process_"))
async def process_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    app_id = int(callback.data.split("_")[1])
    db.update_status(app_id, "processed")
    
    await callback.answer("✅ Заявка отмечена как обработанная")
    application = db.get_application_by_id(app_id)
    if application:
        app_text = format_application_detailed(application)
        await callback.message.edit_text(app_text)
        await callback.message.edit_reply_markup(get_admin_applications_keyboard(app_id))

@dp.callback_query(lambda c: c.data.startswith("details_"))
async def details_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    app_id = int(callback.data.split("_")[1])
    application = db.get_application_by_id(app_id)
    
    if application:
        app_text = format_application_detailed(application)
        keyboard = get_admin_applications_keyboard(app_id)
        await callback.message.answer(app_text, reply_markup=keyboard)
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    app_id = int(callback.data.split("_")[1])
    db.delete_application(app_id)
    
    await callback.answer("🗑️ Заявка удалена")
    await callback.message.edit_text(f"🗑️ Заявка #{app_id} удалена")

@dp.callback_query(lambda c: c.data.startswith("message_"))
async def message_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    app_id = int(callback.data.split("_")[1])
    application = db.get_application_by_id(app_id)
    
    if application:
        user_id = application[1]
        await callback.message.answer(f"Напишите сообщение для пользователя (ID: {user_id}):")
        # Здесь можно реализовать сохранение состояния для отправки сообщения
    
    await callback.answer()

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
