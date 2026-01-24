import asyncio
import logging
import sys
import os
from dotenv import load_dotenv
import threading
from health import run_health_server


health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

load_dotenv()


BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

print("=" * 50)
print("ПРОВЕРКА ЗАПУСКА БОТА")
print("=" * 50)
print(f"BOT_TOKEN: {'УСТАНОВЛЕН' if BOT_TOKEN else 'ОТСУТСТВУЕТ!'}")
print(f"ADMIN_ID: {ADMIN_ID if ADMIN_ID else 'ОТСУТСТВУЕТ!'}")

if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в .env файле!")
    print("Проверьте что в .env есть строка:")
    print("BOT_TOKEN=8449891460:AAGQRse5Tp_3CqgIrcZsHWW8UtBvcbSeXOA")
    sys.exit(1)

if not ADMIN_ID:
    print("❌ ОШИБКА: ADMIN_ID не найден в .env файле!")
    sys.exit(1)

print("=" * 50)
print("Запускаем бота...")

async def run_bot():
    try:
        from aiogram import Bot, Dispatcher
        from aiogram.fsm.storage.memory import MemoryStorage
        
        from bot import dp, bot
        from admin_panel import setup_admin_handlers
        
        # Настраиваем логирование
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Настраиваем админ-панель
        setup_admin_handlers(dp)
        
        print("✅ Бот успешно запущен!")
        print("📱 Найти бота в Telegram: @CLA_on_bot")
        print("📝 Отправьте команду: /start")
        print("👨‍💼 Для админа: /admin")
        print("=" * 50)
        
        await dp.start_polling(bot)
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n✅ Бот остановлен")
    except Exception as e:

        print(f"\n❌ Критическая ошибка: {e}")
