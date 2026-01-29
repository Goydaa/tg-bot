import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import os
from dotenv import load_dotenv
from aiohttp import web

from database import Database
from utils import validate_email, validate_phone, validate_telegram_username, validate_date, validate_time, get_next_dates, get_time_slots

load_dotenv()

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
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Запись на занятие")],
        [KeyboardButton(text="❓ Вопрос по курсу")],
        [KeyboardButton(text="📋 Прочее")],
        [KeyboardButton(text="📊 Статистика")]
    ], resize_keyboard=True)

def get_contact_type_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📧 Email")],
        [KeyboardButton(text="📞 Телефон")],
        [KeyboardButton(text="👤 Telegram")]
    ], resize_keyboard=True)

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
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать!\nВыберите тип обращения:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = "/start - Начать\n/help - Справка\n/stats - Статистика\n/cancel - Отмена\n"
    if message.from_user.id == ADMIN_ID:
        help_text += "\nАдмин:\n/admin\n/applications\n/view_all\n/search [ID]\n/check_reminders\n/test_reminder"
    await message.answer(help_text)

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    stats = db.get_stats()
    await message.answer(f"📊 Статистика:\nВсего: {stats['total']}\nНовых: {stats['new']}\nОбработано: {stats['processed']}")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👨‍💼 Панель администратора:", reply_markup=get_admin_main_keyboard())
    else:
        await message.answer("⛔ Нет доступа")

@dp.message(Command("check_reminders"))
async def cmd_check_reminders(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    reminders = db.get_due_reminders()
    if not reminders:
        await message.answer("✅ Нет напоминаний")
        return
    
    text = "⏰ НАПОМИНАНИЯ:\n\n"
    for i, reminder in enumerate(reminders[:10], 1):
        app_id, reminder_id, user_id, username = reminder[0], reminder[1], reminder[2], reminder[3]
        application = db.get_application_by_id(app_id)
        if application:
            date_display = datetime.strptime(application[8], '%Y-%m-%d').strftime('%d.%m.%Y')
            text += f"{i}. #{app_id} | {application[3]} | {date_display}"
            if user_id == ADMIN_ID:
                text += " 👨‍💼"
            text += "\n"
    
    if len(reminders) > 10:
        text += f"\n... и еще {len(reminders) - 10}"
    text += f"\n\nВсего: {len(reminders)}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить все", callback_data="admin_send_all_reminders")]
    ])
    await message.answer(text, reply_markup=keyboard)

@dp.message(F.text.in_(["📝 Запись на занятие", "❓ Вопрос по курсу", "📋 Прочее"]))
async def process_application_type(message: types.Message, state: FSMContext):
    app_type = {
        "📝 Запись на занятие": "запись",
        "❓ Вопрос по курсу": "вопрос",
        "📋 Прочее": "прочее"
    }[message.text]
    await state.update_data(application_type=app_type)
    await state.set_state(ApplicationStates.waiting_for_name)
    await message.answer("👤 Ваше полное имя:", reply_markup=get_cancel_keyboard())

@dp.message(ApplicationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    await state.update_data(full_name=message.text)
    await state.set_state(ApplicationStates.waiting_for_contact_type)
    await message.answer("📱 Способ связи:", reply_markup=get_contact_type_keyboard())

@dp.message(ApplicationStates.waiting_for_contact_type)
async def process_contact_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    contact_type_map = {"📧 Email": "email", "📞 Телефон": "phone", "👤 Telegram": "telegram"}
    if message.text not in contact_type_map:
        await message.answer("Выберите способ связи:", reply_markup=get_contact_type_keyboard())
        return
    
    contact_type = contact_type_map[message.text]
    await state.update_data(contact_type=contact_type)
    await state.set_state(ApplicationStates.waiting_for_contact)
    
    prompt_text = {
        "email": "📧 Ваш email:",
        "phone": "📞 Ваш телефон:",
        "telegram": "👤 Ваш Telegram:"
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
        error_msg = "❌ Неверный email"
    elif contact_type == "phone":
        is_valid = validate_phone(contact_data)
        error_msg = "❌ Неверный телефон"
    else:
        if contact_data.startswith('@'):
            contact_data = contact_data[1:]
        is_valid = validate_telegram_username(contact_data)
        error_msg = "❌ Неверный Telegram"
    
    if not is_valid:
        await message.answer(error_msg, reply_markup=get_cancel_keyboard())
        return
    
    await state.update_data(contact_data=contact_data)
    
    if data['application_type'] == 'запись':
        await state.set_state(ApplicationStates.waiting_for_date)
        dates = get_next_dates(7)
        dates_text = "📅 Выберите дату:\n\n"
        for date_info in dates:
            dates_text += f"• {date_info['display']}\n"
        dates_text += "\nИли ❌ Без даты"
        await message.answer(dates_text, reply_markup=get_date_keyboard())
    else:
        await state.set_state(ApplicationStates.waiting_for_message)
        await message.answer("💬 Ваш вопрос:", reply_markup=get_cancel_keyboard())

@dp.message(ApplicationStates.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    if message.text == "❌ Без даты":
        await state.update_data(appointment_date=None)
        await state.set_state(ApplicationStates.waiting_for_message)
        await message.answer("💬 Ваш вопрос:", reply_markup=get_cancel_keyboard())
        return
    
    try:
        date_obj = datetime.strptime(message.text, '%d.%m.%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        if not validate_date(formatted_date):
            raise ValueError
        await state.update_data(appointment_date=formatted_date)
        await state.set_state(ApplicationStates.waiting_for_time)
        times = get_time_slots()
        times_text = "⏰ Выберите время:\n\n"
        for time in times:
            times_text += f"• {time}\n"
        times_text += "\nИли ❌ Без времени"
        await message.answer(times_text, reply_markup=get_time_keyboard())
    except:
        await message.answer("❌ Неверная дата", reply_markup=get_date_keyboard())

@dp.message(ApplicationStates.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    if message.text == "❌ Без времени":
        await state.update_data(appointment_time=None)
    else:
        if not validate_time(message.text):
            await message.answer("❌ Неверное время", reply_markup=get_time_keyboard())
            return
        await state.update_data(appointment_time=message.text)
    
    await state.set_state(ApplicationStates.waiting_for_message)
    await message.answer("💬 Ваш вопрос:", reply_markup=get_cancel_keyboard())

@dp.message(ApplicationStates.waiting_for_message)
async def process_message(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cmd_cancel(message, state)
        return
    
    user_data = await state.get_data()
    
    app_id = db.add_application(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=user_data['full_name'],
        contact_type=user_data['contact_type'],
        contact_data=user_data['contact_data'],
        app_type=user_data['application_type'],
        message=message.text,
        appointment_date=user_data.get('appointment_date'),
        appointment_time=user_data.get('appointment_time')
    )
    
    # Уведомление админу
    try:
        admin_text = f"📝 НОВАЯ ЗАЯВКА #{app_id}\n"
        admin_text += f"👤 {user_data['full_name']}\n"
        if user_data.get('appointment_date'):
            date_display = datetime.strptime(user_data['appointment_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            admin_text += f"📅 {date_display}"
            if user_data.get('appointment_time'):
                admin_text += f" ⏰ {user_data['appointment_time']}"
            admin_text += "\n"
        admin_text += f"💬 {message.text[:50]}..."
        keyboard = get_admin_applications_keyboard(app_id)
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=keyboard)
    except:
        pass
    
    # Ответ пользователю
    confirmation = "✅ Заявка принята!\n\n"
    confirmation += f"👤 {user_data['full_name']}\n"
    if user_data.get('appointment_date'):
        date_display = datetime.strptime(user_data['appointment_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        confirmation += f"📅 {date_display}\n"
        if user_data.get('appointment_time'):
            confirmation += f"⏰ {user_data['appointment_time']}\n"
    confirmation += "\nСвяжемся с вами!"
    await message.answer(confirmation, reply_markup=get_main_keyboard())
    
    # Добавление напоминания
    if user_data.get('appointment_date'):
        reminder_date = datetime.strptime(user_data['appointment_date'], '%Y-%m-%d')
        reminder_date = reminder_date.replace(day=reminder_date.day - 1)
        db.add_reminder(app_id, reminder_date.strftime('%Y-%m-%d'))
    
    await state.clear()

@dp.message(F.text == "📊 Статистика")
async def show_stats_button(message: types.Message):
    await cmd_stats(message)

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    action = callback.data
    
    if action == "admin_new":
        apps = db.get_applications('new')
        if apps:
            await callback.message.answer(f"📋 Новых: {len(apps)}")
            for app in apps[:5]:
                text = f"#{app[0]} | {app[3]} | {app[6]}\n{app[7][:50]}..."
                keyboard = get_admin_applications_keyboard(app[0])
                await callback.message.answer(text, reply_markup=keyboard)
        else:
            await callback.message.answer("📭 Нет новых")
    
    elif action == "admin_all":
        apps = db.get_all_applications()
        if not apps:
            await callback.message.answer("📭 Нет заявок")
            return
        
        new = [a for a in apps if a[11] == 'new']
        processed = [a for a in apps if a[11] != 'new']
        
        text = f"📋 ВСЕ: {len(apps)}\n🆕 Новых: {len(new)}\n✅ Обработано: {len(processed)}"
        await callback.message.answer(text)
    
    elif action == "admin_stats":
        stats = db.get_stats()
        await callback.message.answer(f"📊 Всего: {stats['total']}\nНовых: {stats['new']}\nОбработано: {stats['processed']}")
    
    elif action == "admin_search":
        await callback.message.answer("Введите: /search [ID]")
    
    elif action == "admin_check_reminders":
        reminders = db.get_due_reminders()
        if not reminders:
            await callback.message.answer("✅ Нет напоминаний")
            return
        
        text = "⏰ НАПОМИНАНИЯ:\n\n"
        for i, reminder in enumerate(reminders[:10], 1):
            app_id, reminder_id, user_id, username = reminder[0], reminder[1], reminder[2], reminder[3]
            application = db.get_application_by_id(app_id)
            if application:
                date_display = datetime.strptime(application[8], '%Y-%m-%d').strftime('%d.%m.%Y')
                text += f"{i}. #{app_id} | {application[3]} | {date_display}\n"
        
        if len(reminders) > 10:
            text += f"\n... и еще {len(reminders) - 10}"
        text += f"\n\nВсего: {len(reminders)}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить все", callback_data="admin_send_all_reminders")]
        ])
        await callback.message.answer(text, reply_markup=keyboard)
    
    elif action == "admin_send_all_reminders":
        reminders = db.get_due_reminders()
        if not reminders:
            await callback.message.answer("✅ Нет напоминаний")
            return
        
        sent = 0
        failed = 0
        
        await callback.message.answer(f"⏳ Отправка {len(reminders)}...")
        
        for reminder in reminders:
            app_id, reminder_id, user_id, username = reminder[0], reminder[1], reminder[2], reminder[3]
            application = db.get_application_by_id(app_id)
            
            if application:
                date_display = datetime.strptime(application[8], '%Y-%m-%d').strftime('%d.%m.%Y')
                time_text = f" в {application[9]}" if application[9] else ""
                reminder_text = f"🔔 НАПОМИНАНИЕ!\n\nВстреча завтра ({date_display}){time_text}\n\nПодготовьтесь!"
                
                try:
                    await bot.send_message(user_id, reminder_text)
                    db.mark_reminder_sent(reminder_id)
                    sent += 1
                except Exception as e:
                    # Для админа пробуем через callback
                    if user_id == ADMIN_ID:
                        try:
                            await callback.message.answer(f"🔔 ДЛЯ ТЕБЯ!\n\nТвоя встреча завтра ({date_display}){time_text}")
                            db.mark_reminder_sent(reminder_id)
                            sent += 1
                            continue
                        except:
                            pass
                    failed += 1
        
        report = f"📊 ОТЧЕТ:\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}\n📋 Всего: {len(reminders)}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Проверить", callback_data="admin_check_reminders")]
        ])
        await callback.message.answer(report, reply_markup=keyboard)
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("process_"))
async def process_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    app_id = int(callback.data.split("_")[1])
    db.update_status(app_id, "processed")
    await callback.answer("✅ Обработано")

@dp.callback_query(lambda c: c.data.startswith("details_"))
async def details_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    app_id = int(callback.data.split("_")[1])
    app = db.get_application_by_id(app_id)
    if app:
        text = f"📋 #{app[0]}\n👤 {app[3]}\n📱 {app[5]}: {app[4]}\n📅 {app[8] or 'Нет'}\n⏰ {app[9] or 'Нет'}\n💬 {app[7]}\n📊 {app[11]}"
        keyboard = get_admin_applications_keyboard(app_id)
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_callback_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    app_id = int(callback.data.split("_")[1])
    db.delete_application(app_id)
    await callback.answer("🗑️ Удалено")
    await callback.message.edit_text(f"🗑️ #{app_id} удалена")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено", reply_markup=get_main_keyboard())

@dp.message(Command("test_reminder"))
async def cmd_test_reminder(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    from datetime import timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    app_id = db.add_application(
        user_id=message.from_user.id,
        username="admin_test",
        full_name="Тест Админ",
        contact_type="telegram",
        contact_data="admin",
        app_type="запись",
        message="Тест напоминания",
        appointment_date=tomorrow,
        appointment_time="10:00"
    )
    
    db.add_reminder(app_id, today)
    await message.answer(f"✅ Тест заявка #{app_id} создана\nПроверь /check_reminders")

async def health_check(request):
    return web.Response(text="OK")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    return runner

async def main():
    http_server = await start_http_server()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    await dp.start_polling(bot)
    await http_server.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
