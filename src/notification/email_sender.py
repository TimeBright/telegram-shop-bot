import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация Яндекс почты
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 465
YANDEX_PASSWORD = os.getenv('YANDEX_PASSWORD')
SENDER_EMAIL = "sale@introlaser.ru"  # Фиксированный адрес отправителя

def create_order_email_template(order_details):
    """Создание красивого HTML шаблона для письма о заказе"""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">🛍️ Новый заказ в магазине!</h2>

        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="font-size: 16px; color: #34495e;">
                ℹ️ <strong>Детали заказа:</strong><br>
                📦 Номер заказа: #{order_details.get('order_id', 'N/A')}<br>
                📅 Дата: {order_details.get('date', 'N/A')}<br>
                💰 Сумма: {order_details.get('amount', '0')} руб.
            </p>
        </div>

        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
            <p style="font-size: 16px; color: #34495e;">
                📍 <strong>Информация о доставке:</strong><br>
                👤 Получатель: {order_details.get('customer_name', 'N/A')}<br>
                📱 Телефон: {order_details.get('phone', 'N/A')}<br>
                ✉️ Email: {order_details.get('email', 'N/A')}<br>
                🏠 Адрес: {order_details.get('address', 'N/A')}
            </p>
        </div>
    </div>
    """

def send_email(
    to_email: str,
    subject: str,
    text_content: str | None = None,
    html_content: str | None = None
) -> bool:
    """
    Отправка email через Яндекс SMTP
    """
    try:
        logger.info(f"Attempting to send email to {to_email}")
        logger.info(f"Subject: {subject}")

        if not YANDEX_PASSWORD:
            logger.error('YANDEX_PASSWORD environment variable must be set')
            return False

        # Создаем сообщение
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email

        # Форматируем текст перед отправкой
        if text_content:
            text_lines = [line.strip() for line in text_content.splitlines() if line.strip()]
            formatted_text = '\n'.join(text_lines)
            msg.attach(MIMEText(formatted_text, 'plain'))
            logger.info("Text content attached to email")
        if html_content:
            msg.attach(MIMEText(html_content, 'html'))
            logger.info("HTML content attached to email")
        elif not text_content:
            logger.error('Either text_content or html_content must be provided')
            return False

        # Отправляем письмо
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, YANDEX_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}", exc_info=True)
        return False