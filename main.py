"""Main bot module."""
import logging
import os
import asyncio
from flask import Flask, request, jsonify
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

# Проверяем наличие токена
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is required")

# Создаем приложение Flask
app = Flask(__name__)

# Создаем объекты бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@app.route('/')
def root():
    """Root endpoint to verify server is running."""
    logger.info("Root endpoint accessed")
    replit_domain = request.headers.get('Host', 'unknown')
    logger.info(f"Current domain: {replit_domain}")
    return jsonify({
        "status": "running",
        "message": "Telegram bot webhook server is operational",
        "webhook_url": f"https://{replit_domain}/webhook"
    })

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook endpoint for Telegram updates."""
    try:
        logger.info("Webhook request received")
        logger.info(f"Headers: {dict(request.headers)}")

        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Expected JSON"}), 400

        update = request.get_json()
        logger.info(f"Update received: {update}")

        # Process the update
        try:
            await dp.process_update(update)
            logger.info("Update processed successfully")
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}", exc_info=True)

        # Формируем ответ с текущим URL
        replit_domain = request.headers.get('Host', 'unknown')
        response = jsonify({"status": "ok"})
        response.headers['X-Replit-URL'] = f"https://{replit_domain}/webhook"
        logger.info(f"Sending response with X-Replit-URL: {response.headers['X-Replit-URL']}")
        return response

    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

async def setup_bot():
    """Initialize bot and register handlers."""
    logger.info("Starting bot setup...")

    # Register handlers
    await register_shop_handlers(dp)
    await register_review_handlers(dp)
    await register_admin_handlers(dp)

    # Initialize database and test data
    init_db()
    await initialize_test_products()

    # Set webhook
    replit_domain = os.getenv('REPL_SLUG', 'localhost')
    webhook_url = f"https://{replit_domain}.repl.co/webhook"
    await bot.delete_webhook()
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

if __name__ == "__main__":
    try:
        logger.info("Starting application...")

        # Initialize bot asynchronously
        asyncio.run(setup_bot())

        # Запускаем Flask приложение
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Starting Flask app on port {port}")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )

    except Exception as e:
        logger.error(f"Application crashed: {str(e)}", exc_info=True)