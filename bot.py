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

def admin_app_kb(app_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Обработано", callback_data=f"done_{app_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"del_{app_id}")],
        [InlineKeyboardButton(text="📝 Подробнее", callback_data=f"view_{app_id}")]
    ])

# ====================
# КОМАНДЫ ДЛЯ ВСЕХ
# ====================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Добро пожаловать!\nВыберите тип обращения:", reply_markup=main_kb())

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    text = "📚 ДОСТУПНЫЕ КОМАНДЫ:\n\n"
    text += "/start - Начать работу\n"
    text += "/help - Показать справку\n"
    text += "/stats - Статистика заявок\n"
    text += "/cancel - Отменить текущее действие"
    
    # ====================
    # КОМАНДЫ АДМИНА
    # ====================
    if message.from_user.id == ADMIN_ID:
        text += "\n\n👨‍💼 КОМАНДЫ АДМИНА:\n"
        text += "/admin - Панель администратора\n"
        text += "/applications - Новые заявки\n"
        text += "/view_all - Все заявки\n"
        text += "/search [ID] - Найти заявку\n"
        text += "/check_reminders - Проверить напоминания"
    
    await message.answer(text)

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    stats = db.get_stats()
    await message.answer(f"📊 Статистика:\nВсего: {stats['total']}\nНовых: {stats['new']}\nОбработано: {stats['processed']}")

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
        [InlineKeyboardButton(text="⏰ Проверить напоминания", callback_data="admin_check_reminders")]
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
        date_obj = datetime.strptime(message.text, '%d.%m.%Y')
        date_str = date_obj.strftime('%Y-%m-%d')
        
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
    
    # Уведомление админу
    try:
        text = f"📝 НОВАЯ ЗАЯВКА #{app_id}\n👤 {data['name']}\n📱 @{data['contact']}\n"
        if data.get('date'):
            date_display = datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            text += f"📅 {date_display}"
            if data.get('time'):
                text += f" ⏰ {data['time']}"
            text += "\n"
        text += f"💬 {message.text[:50]}..."
        await bot.send_message(ADMIN_ID, text, reply_markup=admin_app_kb(app_id))
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
    
    # Добавление напоминания
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

# ====================
# АДМИН КОЛБЭКИ
# ====================
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
            await callback.message.answer(text, reply_markup=admin_app_kb(app[0]))
    
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
        await callback.message.answer("🔍 Использование:\n/search [ID]")
    
    elif action == "admin_check_reminders":
        reminders = db.get_due_reminders()
        if not reminders:
            await callback.message.answer("✅ Нет напоминаний")
            return
        
        text = "⏰ Напоминания для отправки:\n\n"
        sent_count = 0
        
        for rem in reminders:
            app_id, reminder_id, user_id, username = rem
            app = db.get_application_by_id(app_id)
            
            if app and app[7]:
                date = datetime.strptime(app[7], '%Y-%m-%d').strftime('%d.%m.%Y')
                time_text = f" в {app[8]}" if app[8] else ""
                
                # Отправляем напоминание пользователю
                reminder_text = f"🔔 НАПОМИНАНИЕ!\n\nУ вас запланирована встреча завтра ({date}){time_text}\n\nНе забудьте подготовиться!"
                
                try:
                    await bot.send_message(user_id, reminder_text)
                    db.mark_reminder_sent(reminder_id)
                    sent_count += 1
                    text += f"✅ #{app_id} | {date}{time_text}\n"
                except:
                    text += f"❌ #{app_id} | Ошибка отправки\n"
        
        text += f"\n📊 Отправлено: {sent_count} из {len(reminders)}"
        await callback.message.answer(text)
    
    await callback.answer()

# ====================
# ОБРАБОТКА ЗАЯВОК
# ====================
@dp.callback_query(lambda c: c.data.startswith("done_"))
async def done_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    app_id = int(callback.data.split("_")[1])
    db.update_status(app_id, "processed")
    await callback.answer("✅ Обработано")
    await callback.message.edit_text(f"✅ Заявка #{app_id} обработана")

@dp.callback_query(lambda c: c.data.startswith("del_"))
async def del_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    app_id = int(callback.data.split("_")[1])
    db.delete_application(app_id)
    await callback.answer("🗑️ Удалено")
    await callback.message.edit_text(f"🗑️ Заявка #{app_id} удалена")

@dp.callback_query(lambda c: c.data.startswith("view_"))
async def view_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    app_id = int(callback.data.split("_")[1])
    app = db.get_application_by_id(app_id)
    
    if app:
        text = f"📋 ЗАЯВКА #{app[0]}\n\n"
        text += f"👤 Имя: {app[3]}\n"
        text += f"👤 TG: @{app[2] or 'не указан'}\n"
        text += f"🆔 TG ID: {app[1]}\n"
        text += f"📱 Контакт: @{app[4]}\n"
        text += f"📋 Тип: {app[5]}\n"
        text += f"💬 Сообщение:\n{app[6]}\n"
        
        if app[7]:
            date_display = datetime.strptime(app[7], '%Y-%m-%d').strftime('%d.%m.%Y')
            text += f"📅 Дата: {date_display}\n"
            if app[8]:
                text += f"⏰ Время: {app[8]}\n"
        
        text += f"📅 Создана: {app[9]}\n"
        text += f"📊 Статус: {app[10]}\n"
        
        await callback.message.answer(text, reply_markup=admin_app_kb(app_id))
    
    await callback.answer()

# ====================
# КОМАНДЫ АДМИНА
# ====================
@dp.message(Command("search"))
async def search_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /search [ID]")
        return
    
    try:
        app_id = int(args[1])
        app = db.get_application_by_id(app_id)
        
        if not app:
            await message.answer(f"❌ Заявка #{app_id} не найдена")
            return
        
        text = f"🔍 #{app[0]}\n👤 {app[3]}\n📱 @{app[4]}\n"
        if app[7]:
            date_display = datetime.strptime(app[7], '%Y-%m-%d').strftime('%d.%m.%Y')
            text += f"📅 {date_display}"
            if app[8]:
                text += f" ⏰ {app[8]}"
            text += "\n"
        text += f"💬 {app[6]}\n📊 {app[10]}"
        
        await message.answer(text, reply_markup=admin_app_kb(app[0]))
    except ValueError:
        await message.answer("❌ ID должен быть числом")

@dp.message(Command("applications"))
async def applications_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    apps = db.get_applications('new')
    if not apps:
        await message.answer("📭 Нет новых заявок")
        return
    
    await message.answer(f"📋 Новых заявок: {len(apps)}")
    for app in apps[:5]:
        text = f"#{app[0]} | {app[3]} | {app[5]}\n{app[6][:50]}..."
        await message.answer(text, reply_markup=admin_app_kb(app[0]))

@dp.message(Command("view_all"))
async def view_all_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    apps = db.get_all_applications()
    if not apps:
        await message.answer("📭 Нет заявок")
        return
    
    new = len([a for a in apps if a[10] == 'new'])
    await message.answer(f"📋 Всего заявок: {len(apps)}\n🆕 Новых: {new}\n✅ Обработано: {len(apps)-new}")

@dp.message(Command("check_reminders"))
async def check_reminders_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    reminders = db.get_due_reminders()
    if not reminders:
        await message.answer("✅ Нет напоминаний для отправки")
        return
    
    text = "⏰ Напоминания для отправки:\n\n"
    sent_count = 0
    
    for rem in reminders:
        app_id, reminder_id, user_id, username = rem
        app = db.get_application_by_id(app_id)
        
        if app and app[7]:
            date = datetime.strptime(app[7], '%Y-%m-%d').strftime('%d.%m.%Y')
            time_text = f" в {app[8]}" if app[8] else ""
            
            reminder_text = f"🔔 НАПОМИНАНИЕ!\n\nУ вас запланирована встреча завтра ({date}){time_text}\n\nНе забудьте подготовиться!"
            
            try:
                await bot.send_message(user_id, reminder_text)
                db.mark_reminder_sent(reminder_id)
                sent_count += 1
                text += f"✅ #{app_id} | {date}{time_text}\n"
            except:
                text += f"❌ #{app_id} | Ошибка отправки\n"
    
    text += f"\n📊 Отправлено: {sent_count} из {len(reminders)}"
    await message.answer(text)

async def check_reminders():
    """Функция для автоматической проверки напоминаний"""
    while True:
        await asyncio.sleep(3600)  # Проверяем каждый час
        
        reminders = db.get_due_reminders()
        for rem in reminders:
            app_id, reminder_id, user_id, username = rem
            app = db.get_application_by_id(app_id)
            
            if app and app[7]:
                date = datetime.strptime(app[7], '%Y-%m-%d').strftime('%d.%m.%Y')
                time_text = f" в {app[8]}" if app[8] else ""
                
                reminder_text = f"🔔 НАПОМИНАНИЕ!\n\nУ вас запланирована встреча завтра ({date}){time_text}\n\nНе забудьте подготовиться!"
                
                try:
                    await bot.send_message(user_id, reminder_text)
                    db.mark_reminder_sent(reminder_id)
                    print(f"✅ Отправлено напоминание для заявки #{app_id}")
                except Exception as e:
                    print(f"❌ Ошибка отправки напоминания #{app_id}: {e}")

async def main():
    print("🚀 Бот запускается...")
    
    # Запускаем фоновую задачу для проверки напоминаний
    asyncio.create_task(check_reminders())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
