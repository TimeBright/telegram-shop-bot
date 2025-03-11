"""Image processing module for analyzing payment receipts."""
import pytesseract
from PIL import Image, ImageFilter
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
from pdf2image import convert_from_path
import tempfile
import shutil
from datetime import datetime, timedelta
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_moscow_time():
    """Получить текущее время в московском часовом поясе."""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)

def extract_date_from_receipt(text):
    """Извлечение даты из текста чека."""
    try:
        logger.info("Извлекаем дату из текста чека")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": """Извлеки дату из текста чека в формате DD.MM.YYYY. 
                Верни только дату в указанном формате, например: 02.03.2025
                Если дата не найдена, верни 'not_found'."""
            }, {
                "role": "user",
                "content": text
            }])
        date_str = response.choices[0].message.content.strip()
        logger.info(f"Извлеченная дата: {date_str}")

        if date_str == 'not_found':
            return None

        try:
            return datetime.strptime(date_str, '%d.%m.%Y').date()
        except ValueError:
            logger.error(f"Ошибка парсинга даты: {date_str}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при извлечении даты: {str(e)}")
        return None

def is_receipt(text):
    """Проверка, является ли текст платежным документом."""
    try:
        logger.info("Проверяем, является ли текст платежным документом")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": """Ты - эксперт по проверке платежных документов. 
                Определи, является ли данный текст платежным документом (чеком).
                Платежный документ должен содержать:
                1. Сумму платежа (обычно с символом валюты ₽ или RUB)
                2. Дату и время оплаты
                3. Реквизиты получателя платежа - ОБЯЗАТЕЛЬНО должно быть указано одно из:
                   - "ИП Курников А.В."
                   - "Индивидуальный предприниматель Курников Александр Володарович"

                Верни ответ в формате:
                true|реквизиты найдены
                или
                false|причина отказа

                Примеры:
                true|найдено "ИП Курников А.В."
                false|реквизиты ИП не найдены в тексте чека
                false|не является платежным документом"""
            }, {
                "role": "user",
                "content": text
            }])
        result = response.choices[0].message.content.strip().lower()
        logger.info(f"Результат проверки на платежный документ: {result}")

        # Разбираем ответ на статус и причину
        parts = result.split('|')
        is_valid = parts[0] == 'true'
        reason = parts[1] if len(parts) > 1 else None

        if not is_valid:
            logger.warning(f"Чек не прошел проверку. Причина: {reason}")
        else:
            logger.info(f"Чек успешно прошел проверку. Детали: {reason}")

        return is_valid

    except Exception as e:
        logger.error(f"Ошибка при проверке текста на платежный документ: {str(e)}")
        return False

def analyze_receipt(text):
    """Анализ текста платежного документа."""
    try:
        logger.info("Начинаем анализ текста платежного документа")

        if not is_receipt(text):
            logger.info("Текст не является платежным документом")
            return False, None, "Отправленный документ не является платежным чеком"

        # Извлекаем дату из чека
        receipt_date = extract_date_from_receipt(text)
        if not receipt_date:
            logger.info("Не удалось определить дату в чеке")
            return False, None, "Не удалось определить дату в чеке"

        logger.info(f"Чек успешно проверен, дата: {receipt_date}")
        return True, receipt_date, "Чек успешно проверен"

    except Exception as e:
        logger.error(f"Ошибка анализа платежного документа: {str(e)}")
        return False, None, f"Ошибка анализа платежного документа: {str(e)}"

def save_receipt_file(original_file_path, user_id):
    """Сохранение файла чека во временную директорию."""
    try:
        logger.info(f"Сохраняем файл чека для пользователя {user_id}")

        # Создаем директорию для чеков если её нет
        receipts_dir = os.path.join(os.getcwd(), 'temp_receipts')
        if not os.path.exists(receipts_dir):
            os.makedirs(receipts_dir)
            logger.info(f"Создана директория для чеков: {receipts_dir}")

        # Определяем расширение файла
        _, ext = os.path.splitext(original_file_path)

        # Создаем имя файла с текущим временем
        moscow_time = get_moscow_time()
        timestamp = moscow_time.strftime('%Y%m%d_%H%M%S')
        new_filename = f"receipt_{user_id}_{timestamp}{ext}"
        new_file_path = os.path.join(receipts_dir, new_filename)

        # Копируем файл
        shutil.copy2(original_file_path, new_file_path)
        logger.info(f"Файл чека сохранен: {new_file_path}")

        # Устанавливаем время удаления (24 часа от текущего времени)
        expiration_time = moscow_time + timedelta(hours=24)
        logger.info(f"Установлено время удаления: {expiration_time}")

        return new_file_path, expiration_time
    except Exception as e:
        logger.error(f"Ошибка сохранения файла чека: {str(e)}")
        return None, None

def process_image(image_path, user_id):
    """Обработка изображения или PDF."""
    temp_dir = None
    temp_img_path = None
    receipt_path = None

    try:
        logger.info(f"Начинаем обработку файла: {image_path}")
        if not os.path.exists(image_path):
            logger.error(f"Файл не найден: {image_path}")
            return False, None, None, "Файл не найден"

        logger.info(f"Размер входного файла: {os.path.getsize(image_path)} байт")

        # Проверяем тип файла по расширению
        is_pdf = image_path.lower().endswith('.pdf')
        logger.info(f"Тип файла: {'PDF' if is_pdf else 'Изображение'}")

        if is_pdf:
            try:
                # Создаем временную директорию для конвертации PDF
                temp_dir = tempfile.mkdtemp()
                logger.info(f"Создана временная директория: {temp_dir}")

                # Конвертируем первую страницу PDF в изображение
                logger.info("Начинаем конвертацию PDF в изображение")
                images = convert_from_path(
                    image_path,
                    first_page=1,
                    last_page=1,
                    output_folder=temp_dir,
                    fmt='jpeg',
                    use_pdftocairo=True
                )

                if not images:
                    logger.error("Конвертация PDF не вернула изображений")
                    return False, None, None, "Не удалось обработать PDF документ"

                # Сохраняем первое изображение во временный файл
                temp_img_path = os.path.join(temp_dir, 'converted.jpg')
                images[0].save(temp_img_path, 'JPEG')
                logger.info(f"PDF сконвертирован в изображение: {temp_img_path}")
                logger.info(f"Размер сконвертированного изображения: {os.path.getsize(temp_img_path)} байт")

                # Открываем сконвертированное изображение
                img = Image.open(temp_img_path)
                logger.info(f"Изображение успешно открыто, формат: {img.format}, размер: {img.size}")

            except Exception as pdf_error:
                logger.error(f"Ошибка конвертации PDF: {str(pdf_error)}")
                if "poppler" in str(pdf_error).lower():
                    return False, None, None, "Для обработки PDF требуется установка Poppler"
                return False, None, None, f"Ошибка обработки PDF документа: {str(pdf_error)}"
        else:
            # Обработка обычного изображения
            logger.info("Обработка файла как обычного изображения")
            img = Image.open(image_path)
            logger.info(f"Изображение успешно открыто, формат: {img.format}, размер: {img.size}")

        # Общая обработка изображения
        img = img.convert('L')  # Преобразуем в градации серого
        img = img.filter(ImageFilter.SHARPEN)  # Улучшаем четкость
        logger.info("Изображение обработано (конвертировано в ч/б и улучшена четкость)")

        # Пробуем распознать текст с русской локалью
        text = pytesseract.image_to_string(img, lang='rus')
        if not text.strip():
            logger.info("Не удалось распознать текст с русской локалью, пробуем без указания языка")
            text = pytesseract.image_to_string(img)

        logger.info("OCR обработка завершена")
        logger.info(f"Распознанный текст (первые 100 символов): {text[:100]}...")

        if not text.strip():
            return False, None, None, "Не удалось распознать текст на изображении"

        # Анализируем текст чека
        is_valid, receipt_date, message = analyze_receipt(text)
        if not is_valid:
            return False, None, None, message

        # Сохраняем файл чека
        receipt_path, expiration_time = save_receipt_file(image_path, user_id)
        if not receipt_path:
            return False, None, None, "Ошибка сохранения файла чека"

        return True, receipt_date, receipt_path, "Чек успешно проверен"

    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}")
        return False, None, None, f"Ошибка обработки файла: {str(e)}"

    finally:
        # Очищаем временные файлы
        try:
            if temp_img_path and os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                logger.info(f"Удален временный файл изображения: {temp_img_path}")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Удалена временная директория: {temp_dir}")
        except Exception as cleanup_error:
            logger.error(f"Ошибка при очистке временных файлов: {str(cleanup_error)}")