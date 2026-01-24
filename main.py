import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("ЗАПУСК БОТА КЛАССОНОЛАЙН НА RAILWAY")
print("=" * 50)

async def main():
    try:
        from aiogram import Bot, Dispatcher
        from aiogram.fsm.storage.memory import MemoryStorage
        
        
        bot = Bot(token=os.getenv('BOT_TOKEN'))
        dp = Dispatcher(storage=MemoryStorage())
        
        
        import bot as bot_module
        
        
        from admin_panel import setup_admin_handlers
        setup_admin_handlers(dp)
        
        print("=" * 50)
        print("✅ БОТ УСПЕШНО ЗАПУЩЕН НА RAILWAY!")
        print("=" * 50)
        print("\n📱 Найти бота в Telegram: @CLA_on_bot")
        print("📝 Отправьте команду: /start")
        print("👨‍💼 Для админа: /admin")
        print("=" * 50)
        
        
        await dp.start_polling(bot)
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("\nПроверьте зависимости в requirements.txt")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Бот остановлен")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")

