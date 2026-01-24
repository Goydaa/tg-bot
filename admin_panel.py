from aiogram import types
from aiogram.filters import Command
from database import Database
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = int(os.getenv('ADMIN_ID'))
db = Database()

def get_admin_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📋 Новые заявки", callback_data="admin_view_new")],
        [types.InlineKeyboardButton(text="📊 Все заявки", callback_data="admin_view_all")],
        [types.InlineKeyboardButton(text="📈 Статистика", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="🗑️ Очистить старые", callback_data="admin_cleanup")]
    ])

def setup_admin_handlers(dp):
    @dp.message(Command("applications"))
    async def cmd_applications(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("⛔ Доступ запрещен")
            return
        
        applications = db.get_applications('new')
        
        if not applications:
            await message.answer("📭 Нет новых заявок")
            return
        
        for app in applications[:10]:
            app_text = format_application(app)
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✅ Обработано", callback_data=f"process_{app[0]}"),
                 types.InlineKeyboardButton(text="📝 Просмотреть", callback_data=f"view_{app[0]}")]
            ])
            
            await message.answer(app_text, reply_markup=keyboard)
    
    @dp.message(Command("view_new"))
    async def cmd_view_new(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        
        applications = db.get_applications('new')
        await send_applications_list(message, applications, "Новые заявки:")
    
    @dp.message(Command("view_all"))
    async def cmd_view_all(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        
        applications = db.get_all_applications()
        await send_applications_list(message, applications, "Все заявки:")
    
    @dp.message(Command("stats_full"))
    async def cmd_stats_full(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            return
        
        stats = db.get_stats()
        applications = db.get_all_applications()
        
        type_stats = {}
        for app in applications:
            app_type = app[6]
            type_stats[app_type] = type_stats.get(app_type, 0) + 1
        
        stats_text = "📊 Полная статистика:\n\n"
        stats_text += f"Всего заявок: {stats['total']}\n"
        stats_text += f"Новых: {stats['new']}\n"
        stats_text += f"Обработано: {stats['processed']}\n\n"
        stats_text += "По типам:\n"
        
        for app_type, count in type_stats.items():
            stats_text += f"• {app_type}: {count}\n"
        
        await message.answer(stats_text)
    
    @dp.callback_query(lambda c: c.data.startswith("admin_"))
    async def admin_callback_handler(callback: types.CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("⛔ Доступ запрещен")
            return
        
        action = callback.data
        
        if action == "admin_view_new":
            applications = db.get_applications('new')
            await send_applications_list(callback.message, applications, "Новые заявки:")
        
        elif action == "admin_view_all":
            applications = db.get_all_applications()
            await send_applications_list(callback.message, applications, "Все заявки:")
        
        elif action == "admin_stats":
            stats = db.get_stats()
            await callback.message.answer(
                f"📊 Статистика:\n\n"
                f"Всего заявок: {stats['total']}\n"
                f"Новых: {stats['new']}\n"
                f"Обработано: {stats['processed']}"
            )
        
        elif action == "admin_cleanup":
            await callback.message.answer("🗑️ Функция очистки в разработке")
        
        await callback.answer()
    
    @dp.callback_query(lambda c: c.data.startswith("process_"))
    async def process_callback_handler(callback: types.CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("⛔ Доступ запрещен")
            return
        
        app_id = int(callback.data.split("_")[1])
        db.update_status(app_id, "processed")
        
        await callback.answer("✅ Заявка отмечена как обработанная")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.edit_text(f"{callback.message.text}\n\n✅ Обработано")
    
    @dp.callback_query(lambda c: c.data.startswith("view_"))
    async def view_callback_handler(callback: types.CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("⛔ Доступ запрещен")
            return
        
        app_id = int(callback.data.split("_")[1])
        application = db.get_application_by_id(app_id)
        
        if application:
            app_text = format_application(application, detailed=True)
            await callback.message.answer(app_text)
        
        await callback.answer()

def format_application(application, detailed=False):
    app_id, user_id, username, full_name, contact_type, contact_data, app_type, message, date, time, created_at, status = application
    
    if date:
        text = "📅 Встреча:\n\n"
        text += f"🆔 {app_id}\n"
        text += f"👤 {full_name}\n"
        text += f"📅 {date}"
        if time:
            text += f" ⏰ {time}\n"
        else:
            text += "\n"
        
        contact_display = f"@{contact_data}" if contact_type == 'telegram' else contact_data
        text += f"📞 {contact_display}\n"
    else:
        text = f"📋 Заявка #{app_id}\n\n"
        text += f"👤 {full_name}\n"
        text += f"📱 {contact_type}: {contact_data}\n"
    
    if detailed:
        text += f"\n📝 Тип: {app_type}\n"
        text += f"💬 Сообщение: {message}\n"
        text += f"📅 Создана: {created_at}\n"
        text += f"🔧 Статус: {status}\n"
        text += f"🆔 ID пользователя: {user_id}\n"
        text += f"👤 Username: @{username if username else 'не указан'}"
    else:
        text += f"\n📝 {app_type}\n"
        text += f"💬 {message[:50]}..."
    
    return text

async def send_applications_list(message: types.Message, applications, title):
    if not applications:
        await message.answer(f"{title}\n\n📭 Заявок нет")
        return
    
    text = f"{title}\n\n"
    
    for i, app in enumerate(applications[:20], 1):
        app_id, _, _, full_name, _, _, app_type, message, date, _, created_at, _ = app
        
        if date:
            date_display = date
            if app[9]:
                date_display += f" {app[9]}"
            
            text += f"{i}. 🆔{app_id} 👤{full_name} 📅{date_display}\n"
        else:
            text += f"{i}. 🆔{app_id} 👤{full_name} 📝{app_type}\n"
    
    await message.answer(text)