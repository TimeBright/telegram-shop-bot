"""Bot module for handling payment receipt analysis."""
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .image_processor import process_image  # Обновлен импорт

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определение состояний
class ReceiptStates(StatesGroup):
    waiting_for_receipt = State()

async def receipt_handler(message: Message, state: FSMContext):
    """Обработчик команды /check_receipt"""
    try:
        logger.info(f"Получена команда check_receipt от пользователя {message.from_user.id}")
        await message.answer(
            "📝 Отправьте фотографию чека для проверки.\n"
            "Я помогу проверить платежный документ и извлечь из него информацию."
        )
        await state.set_state(ReceiptStates.waiting_for_receipt)
        logger.info(f"Установлено состояние waiting_for_receipt для пользователя {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка в receipt_handler: {str(e)}", exc_info=True)
        await message.answer("Произошла ошибка при обработке команды. Попробуйте позже.")

async def handle_photo(message: Message, state: FSMContext):
    """Обработчик фотографий в режиме анализа платежных документов"""
    try:
        logger.info(f"Получено фото от пользователя {message.from_user.id}")
        current_state = await state.get_state()

        if current_state != ReceiptStates.waiting_for_receipt.state:
            logger.info(f"Пропуск обработки фото - неверное состояние: {current_state}")
            return

        if not message.photo:
            await message.answer("Пожалуйста, отправьте фотографию платежного документа")
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
            temp_file = f"temp_receipt_{message.from_user.id}.jpg"
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

async def register_receipt_handlers(dp: Dispatcher):
    """Регистрация обработчиков для анализа платежных документов"""
    try:
        logger.info("Начало регистрации обработчиков платежных документов")

        # Регистрируем обработчик команды /check_receipt
        dp.message.register(receipt_handler, Command("check_receipt"))
        logger.info("Зарегистрирован обработчик команды check_receipt")

        # Регистрируем обработчик фотографий
        dp.message.register(handle_photo, ReceiptStates.waiting_for_receipt)
        logger.info("Зарегистрирован обработчик фотографий чеков")

        logger.info("Обработчики платежных документов успешно зарегистрированы")
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков платежных документов: {str(e)}")
        raise