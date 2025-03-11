"""Main bot module."""
import logging
import os
import asyncio
from quart import Quart, request
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from src.shop import register_shop_handlers
from src.shop.database import init_db
from src.shop.main import initialize_test_products
from src.review_handler.bot import register_review_handlers
from src.shop.admin_handlers import register_admin_handlers
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Проверка наличия токена
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is required")

# Создаем Quart приложение для webhook
app = Quart(__name__)

# Создаем объекты бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@app.route('/')
async def root():
    """Health check endpoint."""
    logger.info("Health check accessed")
    webhook_info = await bot.get_webhook_info()
    return {
        "status": "ok",
        "message": "Bot webhook server is running",
        "webhook_url": webhook_info.url,
        "pending_updates": webhook_info.pending_update_count
    }

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook endpoint for Telegram updates."""
    try:
        if not request.is_json:
            logger.error("Invalid content type")
            return {"ok": False, "error": "Invalid content type"}, 400

        update = await request.get_json()
        logger.info("Received webhook update")

        await dp.feed_update(bot, update)
        logger.info("Update processed successfully")

        return {"ok": True}
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

async def setup_webhook():
    """Setup webhook configuration."""
    try:
        # Используем предоставленный домен Railway
        webhook_host = "stunning-learning-production.up.railway.app"
        webhook_url = f"https://{webhook_host}/webhook"

        logger.info("Removing old webhook configuration...")
        await bot.delete_webhook()

        logger.info(f"Setting webhook to: {webhook_url}")
        await bot.set_webhook(webhook_url)

        # Добавляем небольшую задержку для гарантии установки webhook
        await asyncio.sleep(1)

        # Проверяем, что webhook установлен
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url == webhook_url:
            logger.info("Webhook successfully configured")
            # Проверяем, есть ли ожидающие обновления
            if webhook_info.pending_update_count > 0:
                logger.info(f"Found {webhook_info.pending_update_count} pending updates")
            return True
        else:
            raise ValueError(f"Failed to set webhook. Expected {webhook_url}, got {webhook_info.url}")

    except Exception as e:
        logger.error(f"Error setting up webhook: {str(e)}", exc_info=True)
        raise

@app.before_serving
async def startup():
    """Initialize bot before starting server."""
    try:
        logger.info("Starting bot initialization...")

        # Register handlers
        await register_shop_handlers(dp)
        await register_review_handlers(dp)
        await register_admin_handlers(dp)

        # Initialize database
        init_db()
        await initialize_test_products()

        # Setup webhook
        if not await setup_webhook():
            raise ValueError("Failed to setup webhook")

        logger.info("Bot initialization completed successfully")
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting bot on port {port}")
    app.run(host='0.0.0.0', port=port)