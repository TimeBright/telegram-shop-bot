"""Bot module for handling review analysis."""
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .image_processor import process_image

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определение состояний
class ReviewStates(StatesGroup):
    waiting_for_review = State()

async def analyze_handler(message: Message, state: FSMContext):
    """Обработчик команды /o"""
    try:
        logger.info(f"Получена команда o от пользователя {message.from_user.id}")
        await message.answer(
            "📝 Отправьте скриншот отзыва для анализа.\n"
            "Я помогу составить профессиональный ответ на отзыв клиента."
        )
        await state.set_state(ReviewStates.waiting_for_review)
        logger.info(f"Установлено состояние waiting_for_review для пользователя {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка в analyze_handler: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды. Попробуйте позже.")

async def handle_photo(message: Message, state: FSMContext):
    """Обработчик фотографий в режиме анализа отзывов"""
    try:
        logger.info(f"Получено фото от пользователя {message.from_user.id}")
        current_state = await state.get_state()

        if current_state != ReviewStates.waiting_for_review.state:
            logger.info(f"Пропуск обработки фото - неверное состояние: {current_state}")
            return

        if not message.photo:
            await message.answer("Пожалуйста, отправьте фотографию отзыва")
            return

        processing_msg = await message.answer("🔄 Обрабатываю изображение...")

        try:
            # Получаем файл фотографии
            photo = message.photo[-1]
            file = await message.bot.get_file(photo.file_id)
            logger.info(f"Получен файл: {file.file_id}")

            # Скачиваем файл
            photo_bytes = await message.bot.download_file(file.file_path)
            logger.info("Фото успешно скачано")

            # Создаем временный файл
            temp_file = f"temp_{message.from_user.id}.jpg"
            with open(temp_file, 'wb') as f:
                f.write(photo_bytes.read())
            logger.info(f"Создан временный файл: {temp_file}")

            # Обработка изображения
            result = process_image(temp_file)
            logger.info("Изображение обработано")

            # Удаляем временный файл
            os.remove(temp_file)
            logger.info("Временный файл удален")

            # Отправляем результат
            await message.answer(result)

        except Exception as e:
            logger.error(f"Ошибка при обработке фото: {str(e)}", exc_info=True)
            await message.answer(
                "❌ Произошла ошибка при обработке изображения.\n"
                "Пожалуйста, убедитесь, что изображение четкое и попробуйте снова."
            )
        finally:
            # Удаляем сообщение о процессе обработки
            await processing_msg.delete()

        # Сбрасываем состояние после обработки
        await state.clear()
        logger.info(f"Состояние сброшено для пользователя {message.from_user.id}")

    except Exception as e:
        logger.error(f"Общая ошибка в handle_photo: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке изображения.\n"
            "Пожалуйста, попробуйте снова."
        )
        await state.clear()

async def register_review_handlers(dp: Dispatcher):
    """Регистрация обработчиков для анализа отзывов"""
    try:
        logger.info("Начало регистрации обработчиков отзывов")

        # Регистрируем обработчик команды /o
        dp.message.register(analyze_handler, Command("o"))
        logger.info("Зарегистрирован обработчик команды o")

        # Регистрируем обработчик фотографий
        dp.message.register(handle_photo, ReviewStates.waiting_for_review)
        logger.info("Зарегистрирован обработчик фотографий")

        logger.info("Обработчики отзывов успешно зарегистрированы")
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков отзывов: {str(e)}")
        raise