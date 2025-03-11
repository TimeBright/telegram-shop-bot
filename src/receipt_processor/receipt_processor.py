"""Receipt processing module for analyzing payment receipts."""
import logging
import pytesseract
from PIL import Image, ImageFilter
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_payment_details(text):
    """Извлечение деталей платежа из текста."""
    try:
        # Регулярные выражения для поиска суммы, даты и времени
        amount_pattern = r'\b\d+[.,]?\d*\s?(?:RUB|₽|руб\.?)\b'
        date_pattern = r'\b\d{2}[./-]\d{2}[./-]\d{4}\b'
        time_pattern = r'\b\d{2}:\d{2}(?::\d{2})?\b'

        # Поиск значений
        amount = re.search(amount_pattern, text)
        date = re.search(date_pattern, text)
        time = re.search(time_pattern, text)

        return {
            'amount': amount.group(0) if amount else None,
            'date': date.group(0) if date else None,
            'time': time.group(0) if time else None
        }
    except Exception as e:
        logger.error(f"Ошибка при извлечении деталей платежа: {str(e)}")
        return None

def validate_receipt(text, expected_amount=None):
    """Проверка валидности чека через GPT."""
    try:
        logger.info("Начинаем валидацию чека через GPT")

        validation_prompt = f"""Проанализируй текст чека и определи:
        1. Является ли это действительно чеком об оплате
        2. Сумму платежа
        3. Дату и время платежа
        4. Статус платежа (успешно/неуспешно)

        Если указана сумма {expected_amount}, проверь совпадает ли она с суммой в чеке.

        Ответь в формате JSON:
        {{
            "is_valid": true/false,
            "amount": "сумма",
            "datetime": "дата и время",
            "status": "статус",
            "matches_expected": true/false,
            "error": "причина ошибки если есть"
        }}

        Текст чека:
        {text}"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "Ты - эксперт по проверке платежных документов."
            }, {
                "role": "user",
                "content": validation_prompt
            }])

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка при валидации чека: {str(e)}")
        return None

async def process_receipt(image_path, expected_amount=None):
    """Асинхронная обработка изображения чека."""
    try:
        logger.info(f"Начинаем обработку изображения чека: {image_path}")

        # Открываем изображение
        img = Image.open(image_path)
        logger.info("Изображение успешно открыто")

        # Применяем предварительную обработку
        img = img.convert('L')  # Преобразуем в градации серого
        img = img.filter(ImageFilter.SHARPEN)  # Улучшаем четкость

        try:
            # Пробуем распознать текст с русской локалью
            text = pytesseract.image_to_string(img, lang='rus')
            if not text.strip():
                # Если не удалось, пробуем без указания языка
                text = pytesseract.image_to_string(img)
        except Exception as ocr_error:
            logger.error(f"Ошибка OCR: {str(ocr_error)}")
            text = pytesseract.image_to_string(img)

        if not text.strip():
            return {
                "success": False,
                "error": "Не удалось распознать текст на изображении"
            }

        # Извлекаем детали платежа
        payment_details = extract_payment_details(text)
        if not payment_details:
            return {
                "success": False,
                "error": "Не удалось извлечь детали платежа"
            }

        # Валидируем чек через GPT
        validation_result = validate_receipt(text, expected_amount)
        if not validation_result:
            return {
                "success": False,
                "error": "Ошибка валидации чека"
            }

        return {
            "success": True,
            "payment_details": payment_details,
            "validation_result": validation_result
        }

    except Exception as e:
        logger.error(f"Ошибка обработки изображения чека: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }