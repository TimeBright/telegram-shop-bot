"""Bot module for handling receipt analysis."""
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
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
class ReceiptStates(StatesGroup):
    waiting_for_receipt = State()

async def process_receipt_image(message: Message, state: FSMContext):
    """Обработчик изображений чеков"""
    try:
        logger.info(f"Получено изображение чека от пользователя {message.from_user.id}")

        # Проверяем наличие изображения
        if not message.photo:
            await message.answer("Пожалуйста, отправьте фотографию чека")
            return

        # Показываем сообщение о начале обработки
        processing_msg = await message.answer("🔄 Обрабатываю изображение чека...")

        try:
            # Получаем файл
            photo = message.photo[-1]
            file = await message.bot.get_file(photo.file_id)
            logger.info(f"Получен файл: {file.file_id}")

            # Скачиваем файл
            photo_bytes = await message.bot.download_file(file.file_path)
            logger.info("Фото успешно скачано")

            # Создаем временный файл
            temp_file = f"temp_receipt_{message.from_user.id}_{photo.file_unique_id}.jpg"
            with open(temp_file, 'wb') as f:
                f.write(photo_bytes.read())
            logger.info(f"Создан временный файл: {temp_file}")

            # Обработка изображения
            success, receipt_date, receipt_path, message_text = process_image(temp_file, message.from_user.id)
            logger.info(f"Результат обработки: success={success}, date={receipt_date}, message={message_text}")

            if success:
                await message.answer(
                    "✅ Чек успешно проверен\n\n"
                    f"📅 Дата: {receipt_date}\n"
                    "Чек сохранен и отправлен на обработку."
                )
            else:
                await message.answer(
                    f"❌ Ошибка при проверке чека:\n{message_text}\n\n"
                    "Пожалуйста, убедитесь что:\n"
                    "1. Изображение четкое и хорошо читаемое\n"
                    "2. В чеке указаны реквизиты получателя:\n"
                    "   - ИП Курников А.В. или\n"
                    "   - Индивидуальный предприниматель Курников Александр Володарович\n"
                    "3. Видны дата и время оплаты\n"
                    "4. Это действительно чек об оплате\n\n"
                    "Загрузите чек повторно или обратитесь в поддержку, если проблема сохраняется."
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке файла: {str(e)}", exc_info=True)
            await message.answer(
                "❌ Произошла ошибка при обработке чека.\n"
                "Пожалуйста, убедитесь, что изображение четкое и попробуйте снова."
            )
        finally:
            # Удаляем временный файл
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Удален временный файл: {temp_file}")
            except Exception as e:
                logger.error(f"Ошибка при удалении временного файла: {str(e)}")

            # Удаляем сообщение о процессе обработки
            try:
                await processing_msg.delete()
            except Exception as e:
                logger.error(f"Ошибка при удалении сообщения о процессе: {str(e)}")

    except Exception as e:
        logger.error(f"Общая ошибка в process_receipt_image: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке изображения.\n"
            "Пожалуйста, попробуйте позже."
        )

async def register_receipt_handlers(dp: Dispatcher):
    """Регистрация обработчиков для анализа чеков"""
    try:
        logger.info("Начало регистрации обработчиков чеков")
        dp.message.register(process_receipt_image, ReceiptStates.waiting_for_receipt)
        logger.info("Зарегистрирован обработчик чеков")
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков чеков: {str(e)}")
        raise