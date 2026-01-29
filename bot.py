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

from database import Database
from utils import validate_telegram_username, get_next_dates, get_time_slots

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

class States(StatesGroup):
    name = State()
    contact = State()
    message = State()
    date = State()
    time = State()

def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Запись на занятие")],
        [KeyboardButton(text="❓ Вопрос по курсу")],
        [KeyboardButton(text="📋 Прочее")],
        [KeyboardButton(text="📊 Статистика")]
    ], resize_keyboard=True)

def date_kb():
    dates = get_next_dates(7)
    rows = []
    row = []
    for i, date in enumerate(dates):
        row.append(KeyboardButton(text=date['display']))
        if len(row) == 2 or i == len(dates) - 1:
            rows.append(row)
            row = []
    rows.append([KeyboardButton(text="❌ Без даты")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def time_kb():
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

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Добро пожаловать!\nВыберите тип обращения:", reply_markup=main_kb())

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    text = "/start - Начать\n/help - Справка\n/stats - Статистика\n/cancel - Отмена"
    if message.from_user.id == ADMIN_ID:
        text += "\n\nАдмин:\n/admin\n/applications\n/view_all\n/search [id/name]\n/check_reminders"
    await message.answer(text)

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    stats = db.get_stats()
    await message.answer(f"📊 Заявок: {stats['total']}\nНовых: {stats['new']}\nОбработано: {stats['processed']}")

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Новые заявки", callback_data="admin_new")],
        [InlineKeyboardButton(text="📊 Все заявки", callback_data="admin_all")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_search")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⏰ Напоминания", callback_data="admin_reminders")]
    ])
    await message.answer("👨‍💼 Админ-панель:", reply_markup=keyboard)

@dp.message(F.text.in_(["📝 Запись на занятие", "❓ Вопрос по курсу", "📋 Прочее"]))
async def type_handler(message: types.Message, state: FSMContext):
    types_map = {
        "📝 Запись на занятие": "запись",
        "❓ Вопрос по курсу": "вопрос",
        "📋 Прочее": "прочее"
    }
    await state.update_data(type=types_map[message.text])
    await state.set_state(States.name)
    await message.answer("👤 Ваше имя:", reply_markup=cancel_kb())

@dp.message(States.name)
async def name_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_kb())
        return
    
    await state.update_data(name=message.text)
    await state.set_state(States.contact)
    await message.answer("👤 Telegram username:", reply_markup=cancel_kb())

@dp.message(States.contact)
async def contact_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_kb())
        return
    
    contact = message.text.replace('@', '')
    if not validate_telegram_username(contact):
        await message.answer("❌ Неверный username", reply_markup=cancel_kb())
        return
    
    data = await state.get_data()
    await state.update_data(contact=contact)
    
    if data['type'] == 'запись':
        await state.set_state(States.date)
        await message.answer("📅 Выберите дату:", reply_markup=date_kb())
    else:
        await state.set_state(States.message)
        await message.answer("💬 Ваш вопрос:", reply_markup=cancel_kb())

@dp.message(States.date)
async def date_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_kb())
        return
    
    if message.text == "❌ Без даты":
        await state.update_data(date=None)
        await state.set_state(States.message)
        await message.answer("💬 Ваш вопрос:", reply_markup=cancel_kb())
        return
    
    try:
        # Конвертируем из формата дд.мм.гггг в гггг-мм-дд
        date_obj = datetime.strptime(message.text, '%d.%m.%Y')
        date_str = date_obj.strftime('%Y-%m-%d')
        
        # Проверяем, что дата не в прошлом
        if date_obj.date() < datetime.now().date():
            await message.answer("❌ Дата уже прошла", reply_markup=date_kb())
            return
            
        await state.update_data(date=date_str)
        await state.set_state(States.time)
        await message.answer("⏰ Выберите время:", reply_markup=time_kb())
    except:
        await message.answer("❌ Неверный формат даты\nПример: 30.01.2026", reply_markup=date_kb())

@dp.message(States.time)
async def time_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_kb())
        return
    
    if message.text == "❌ Без времени":
        await state.update_data(time=None)
    else:
        # Простая проверка формата времени
        try:
            datetime.strptime(message.text, '%H:%M')
        except:
            await message.answer("❌ Неверное время\nПример: 14:00", reply_markup=time_kb())
            return
        await state.update_data(time=message.text)
    
    await state.set_state(States.message)
    await message.answer("💬 Ваш вопрос:", reply_markup=cancel_kb())

@dp.message(States.message)
async def message_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_kb())
        return
    
    data = await state.get_data()
    
    app_id = db.add_application(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=data['name'],
        contact_data=data['contact'],
        app_type=data['type'],
        message=message.text,
        appointment_date=data.get('date'),
        appointment_time=data.get('time')
    )
    
    # Админу
    try:
        text = f"📝 НОВАЯ ЗАЯВКА #{app_id}\n👤 {data['name']}\n📱 @{data['contact']}\n"
        if data.get('date'):
            date_display = datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            text += f"📅 {date_display}"
            if data.get('time'):
                text += f" ⏰ {data['time']}"
            text += "\n"
        text += f"💬 {message.text[:50]}..."
        await bot.send_message(ADMIN_ID, text)
    except:
        pass
    
    # Пользователю
    text = f"✅ Заявка #{app_id} принята!\n👤 {data['name']}\n📱 @{data['contact']}\n"
    if data.get('date'):
        date_display = datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        text += f"📅 {date_display}"
        if data.get('time'):
            text += f" ⏰ {data['time']}"
        text += "\n"
    text += "\nСвяжемся с вами!"
    await message.answer(text, reply_markup=main_kb())
    
    # Напоминание
    if data.get('date'):
        reminder_date = datetime.strptime(data['date'], '%Y-%m-%d')
        reminder_date = reminder_date.replace(day=reminder_date.day - 1)
        db.add_reminder(app_id, reminder_date.strftime('%Y-%m-%d'))
    
    await state.clear()

@dp.message(Command("cancel"))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено", reply_markup=main_kb())

@dp.message(F.text == "📊 Статистика")
async def stats_btn(message: types.Message):
    await stats_cmd(message)

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    action = callback.data
    
    if action == "admin_new":
        apps = db.get_applications('new')
        if not apps:
            await callback.message.answer("📭 Нет новых")
            return
        for app in apps[:5]:
            text = f"#{app[0]} | {app[3]} | {app[5]}\n{app[6][:50]}..."
            await callback.message.answer(text)
    
    elif action == "admin_all":
        apps = db.get_all_applications()
        if not apps:
            await callback.message.answer("📭 Нет заявок")
            return
        new = len([a for a in apps if a[10] == 'new'])
        await callback.message.answer(f"📋 Всего: {len(apps)}\n🆕 Новых: {new}")
    
    elif action == "admin_stats":
        stats = db.get_stats()
        await callback.message.answer(f"📊 Всего: {stats['total']}\nНовых: {stats['new']}\nОбработано: {stats['processed']}")
    
    elif action == "admin_search":
        await callback.message.answer("🔍 Формат:\n/search id 3\n/search name антон")
    
    elif action == "admin_reminders":
        reminders = db.get_due_reminders()
        if not reminders:
            await callback.message.answer("✅ Нет напоминаний")
            return
        text = "⏰ Напоминания:\n\n"
        for i, rem in enumerate(reminders[:5], 1):
            app_id, reminder_id, user_id, username = rem
            app = db.get_application_by_id(app_id)
            if app and app[7]:
                date = datetime.strptime(app[7], '%Y-%m-%d').strftime('%d.%m')
                text += f"{i}. #{app_id} | {app[3]} | {date}\n"
        await callback.message.answer(text)
    
    await callback.answer()

@dp.message(Command("search"))
async def search_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ Формат: /search [id/name] [значение]")
        return
    
    search_type = args[1].lower()
    query = args[2].strip().lower()
    apps = db.get_all_applications()
    
    if not apps:
        await message.answer("📭 Нет заявок")
        return
    
    found = []
    for app in apps:
        if search_type == "id" and query.isdigit() and int(query) == app[0]:
            found.append(app)
        elif search_type == "name" and query in app[3].lower():
            found.append(app)
    
    if not found:
        await message.answer(f"❌ Не найдено: {query}")
        return
    
    if len(found) == 1:
        app = found[0]
        text = f"🔍 #{app[0]}\n👤 {app[3]}\n📱 @{app[4]}\n📅 {app[7] or 'Нет'}\n⏰ {app[8] or 'Нет'}\n💬 {app[6]}\n📊 {app[10]}"
        await message.answer(text)
    else:
        text = f"🔍 Найдено: {len(found)}\n\n"
        for i, app in enumerate(found[:5], 1):
            text += f"{i}. #{app[0]} | {app[3]} | {app[10]}\n"
        await message.answer(text)

async def main():
    print("🚀 Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

