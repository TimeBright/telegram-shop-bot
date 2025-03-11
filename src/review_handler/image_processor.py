"""Image processing module for analyzing reviews."""
import pytesseract
from PIL import Image, ImageFilter
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def is_review(text):
    """Проверка, является ли текст отзывом клиента."""
    try:
        logger.info("Проверяем, является ли текст отзывом")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": """Ты - эксперт по анализу отзывов. 
                Определи, является ли данный текст отзывом клиента о товаре или услуге.
                Отзыв обычно содержит:
                1. Описание опыта использования
                2. Оценку качества/сервиса
                3. Комментарии о достоинствах/недостатках
                4. Рекомендации другим покупателям

                Ответь только 'true' если это отзыв, или 'false' если нет."""
            }, {
                "role": "user",
                "content": text
            }])
        result = response.choices[0].message.content.strip().lower()
        return result == 'true'
    except Exception as e:
        logger.error(f"Ошибка при проверке текста на отзыв: {str(e)}")
        return False

def analyze_review(text):
    """Анализ текста отзыва с помощью OpenAI."""
    try:
        logger.info("Начинаем анализ текста отзыва")

        # Сначала проверяем, является ли текст отзывом
        if not is_review(text):
            return (
                "❌ Похоже, что отправленный текст не является отзывом клиента.\n\n"
                "Пожалуйста, отправьте скриншот с реальным отзывом, который содержит:\n"
                "• Опыт использования товара/услуги\n"
                "• Оценку качества\n"
                "• Комментарии о плюсах/минусах\n"
                "• Рекомендации другим покупателям"
            )

        logger.info("Текст определен как отзыв, генерируем ответ")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": """Ты - менеджер по работе с клиентами маркетплейса. Тебе присылают отзывы и ты на них отвечаешь. 
                Напиши ответ на отзыв клиента. Обязательно используй эмодзи. Будь дружелюбным и позитивным. 
                Обращайся только на вы. Не используй формальные подписи в конце ответа (такие как "С уважением", "Команда поддержки" и т.п.).
                Не используй слово "привет" в начале ответа. Начинай ответ сразу с благодарности или сути. не напомянай про вопросы типо такого Если вдруг у вас появятся вопросы или возникнут недостатки, будем рады помочь!"""
            }, {
                "role": "user",
                "content": text
            }])
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка анализа отзыва: {str(e)}")
        return f"Ошибка анализа отзыва: {str(e)}"

def process_image(image_path):
    """Обработка изображения."""
    try:
        logger.info(f"Начинаем обработку изображения: {image_path}")

        # Открываем и обрабатываем изображение
        img = Image.open(image_path)
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
            text = pytesseract.image_to_string(img)  # Пробуем без указания языка

        logger.info("OCR обработка завершена")

        if not text.strip():
            return "Не удалось распознать текст на изображении. Пожалуйста, убедитесь что текст четкий и попробуйте снова."

        # Анализируем текст и возвращаем результат
        return analyze_review(text)

    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {str(e)}")
        return f"Ошибка обработки изображения: {str(e)}"