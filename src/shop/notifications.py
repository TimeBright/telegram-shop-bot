"""Module for handling email notifications."""
import os
import logging
from src.notification.email_sender import send_email, create_order_email_template

logger = logging.getLogger(__name__)

async def send_email_notification(to_email: str, subject: str, body: str, order_details: dict = None):
    """Send email notification using SMTP."""
    try:
        logger.info(f"Отправка уведомления на email: {to_email}")
        logger.info(f"Тема: {subject}")

        # Если есть детали заказа, создаем HTML шаблон
        html_content = None
        if order_details:
            html_content = create_order_email_template(order_details)
            logger.info("Created HTML template for order notification")

        # Отправляем письмо
        result = send_email(
            to_email=to_email,
            subject=subject,
            text_content=body,
            html_content=html_content
        )

        if result:
            logger.info(f"Email успешно отправлен на {to_email}")
        else:
            logger.error(f"Не удалось отправить email на {to_email}")
            raise Exception("Failed to send email")

    except Exception as e:
        logger.error(f"Ошибка при отправке email уведомления: {str(e)}", exc_info=True)
        raise