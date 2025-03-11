"""Handlers for delivery checkout process."""
import logging
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from .database import get_db
from .models import Order, OrderItem
from .states import ShopStates
from .protected_handlers import create_base_keyboard

logger = logging.getLogger(__name__)

async def process_delivery_checkout(message: Message, state: FSMContext):
    """Начало оформления доставки"""
    try:
        user_id = message.from_user.id
        logger.info(f"Starting delivery checkout for user {user_id}")

        data = await state.get_data()
        cart = data.get('cart', {})

        if not cart:
            await message.answer(
                "🛒 Ваша корзина пуста. Добавьте товары для оформления заказа.",
                reply_markup=create_base_keyboard()
            )
            return

        # Показываем подробное информационное сообщение о процессе
        total_sum = sum(item['price'] * item['quantity'] for item in cart.values())
        info_message = (
            "📦 Оформление заказа\n\n"
            "Процесс оформления заказа состоит из трех этапов:\n\n"
            "1️⃣ Оформление доставки:\n"
            "- Ввод ФИО получателя\n"
            "- Указание контактного телефона\n"
            "- Ввод адреса доставки\n\n"
            "2️⃣ Оплата заказа:\n"
            "- Оплата через QR-код или по ссылке\n"
            "- Сохранение электронного чека\n"
            "- Загрузка чека для проверки\n\n"
            "3️⃣ Подтверждение заказа:\n"
            "- Автоматическая проверка чека\n"
            "- Подтверждение оплаты\n"
            "- Отправка уведомления\n\n"
            f"💰 Сумма к оплате: {total_sum:,.2f} руб.\n\n"
            "❗️ На каждом этапе вы можете отменить оформление заказа\n"
            "✅ Готовы начать оформление?\n"
        )

        confirm_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Начать оформление")],
                [KeyboardButton(text="❌ Отменить оформление")]
            ],
            resize_keyboard=True
        )

        await message.answer(info_message, reply_markup=confirm_keyboard)
        await state.set_state(ShopStates.WAITING_FOR_CUSTOMER_NAME)
        logger.info(f"Sent checkout info to user {user_id}")

    except Exception as e:
        logger.error(f"Error in process_delivery_checkout: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при оформлении доставки",
            reply_markup=create_base_keyboard()
        )
        await state.clear()

async def process_customer_name(message: Message, state: FSMContext):
    """Обработка имени покупателя"""
    try:
        if message.text == "❌ Отменить оформление":
            await state.clear()
            await message.answer(
                "🛑 Оформление заказа отменено",
                reply_markup=create_base_keyboard()
            )
            return

        if message.text == "✅ Начать оформление":
            # Пользователь подтвердил начало оформления
            await message.answer(
                "👤 Пожалуйста, введите ваше полное имя:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="❌ Отменить оформление")]],
                    resize_keyboard=True
                )
            )
            return

        # Обработка введенного имени
        name = message.text.strip()
        if len(name) < 2:
            await message.answer(
                "⚠️ Пожалуйста, введите корректное имя (минимум 2 символа)"
            )
            return

        await state.update_data(customer_name=name)
        logger.info(f"Saved customer name: {name}")

        # Запрашиваем номер телефона
        phone_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Отправить контакт", request_contact=True)],
                [KeyboardButton(text="❌ Отменить оформление")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "📱 Введите ваш номер телефона или нажмите кнопку 'Отправить контакт':",
            reply_markup=phone_keyboard
        )

        await state.set_state(ShopStates.WAITING_FOR_CUSTOMER_PHONE)

    except Exception as e:
        logger.error(f"Error in process_customer_name: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при сохранении имени",
            reply_markup=create_base_keyboard()
        )
        await state.clear()

async def process_customer_phone(message: Message, state: FSMContext):
    """Обработка телефона покупателя"""
    try:
        if message.text == "❌ Отменить оформление":
            await state.clear()
            await message.answer(
                "🛑 Оформление заказа отменено",
                reply_markup=create_base_keyboard()
            )
            return

        # Проверяем, отправил ли пользователь контакт
        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text.strip()

        # Проверяем формат телефона
        if not re.match(r'^\+?[0-9]{10,12}$', phone.replace(' ', '')):
            await message.answer(
                "⚠️ Пожалуйста, введите корректный номер телефона\n"
                "Например: +79001234567"
            )
            return

        await state.update_data(customer_phone=phone)
        logger.info(f"Saved customer phone: {phone}")

        # Запрашиваем адрес доставки
        address_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❌ Отменить оформление")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            "📍 Пожалуйста, введите адрес доставки:\n\n"
            "Укажите:\n"
            "- Город\n"
            "- Улицу\n"
            "- Номер дома и квартиры\n"
            "- Индекс (если известен)",
            reply_markup=address_keyboard
        )

        await state.set_state(ShopStates.WAITING_FOR_DELIVERY_ADDRESS)

    except Exception as e:
        logger.error(f"Error in process_customer_phone: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при сохранении телефона",
            reply_markup=create_base_keyboard()
        )
        await state.clear()

async def process_delivery_address(message: Message, state: FSMContext):
    """Обработка адреса доставки"""
    try:
        if message.text == "❌ Отменить оформление":
            await state.clear()
            await message.answer(
                "🛑 Оформление заказа отменено",
                reply_markup=create_base_keyboard()
            )
            return

        address = message.text.strip()
        if len(address) < 10:
            await message.answer(
                "⚠️ Пожалуйста, введите более подробный адрес доставки"
            )
            return

        # Сохраняем адрес
        await state.update_data(delivery_address=address)
        data = await state.get_data()
        logger.info(f"Saved delivery address: {address}")

        # Создаем заказ
        try:
            db = get_db()
            order = Order(
                user_id=str(message.from_user.id),
                customer_name=data['customer_name'],
                customer_phone=data['customer_phone'],
                delivery_address=address,
                total_amount=sum(item['price'] * item['quantity'] for item in data['cart'].values()),
                payment_status='pending'
            )
            db.add(order)
            db.commit()
            logger.info(f"Created order {order.id}")

            # Добавляем товары в заказ
            for product_id, item in data['cart'].items():
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=int(product_id),
                    quantity=item['quantity'],
                    price=item['price']
                )
                db.add(order_item)
            db.commit()
            logger.info(f"Added items to order {order.id}")

            # Переходим к этапу оплаты
            payment_info = (
                f"✅ Данные доставки сохранены!\n\n"
                f"📦 Заказ #{order.id}\n"
                f"👤 ФИО: {data['customer_name']}\n"
                f"📱 Телефон: {data['customer_phone']}\n"
                f"📍 Адрес: {address}\n"
                f"💰 Сумма: {order.total_amount:,.2f} руб.\n\n"
                f"💳 Порядок оплаты заказа:\n"
                f"1. Отсканируйте QR-код или перейдите по ссылке для оплаты:\n"
                f"https://qr.nspk.ru/AS20006OKC648VO0845BQH1MD028D7B8?type=01&bank=100000000005&sum=5000&cur=RUB&crc=1443\n\n"
                f"2. После оплаты сохраните электронный чек из банка\n"
                f"3. Прикрепите сохраненный чек для проверки в этот чат\n"
                f"4. Мы проверим чек и поменяем статус заказа на Оформлен\n\n"
                f"⚠️ Заказ будет подтвержден только после успешной проверки чека"
            )

            # Очищаем корзину и сохраняем ID заказа для проверки чека
            await state.set_data({'current_order_id': order.id})
            await state.set_state(ShopStates.WAITING_FOR_PAYMENT_CONFIRMATION)

            await message.answer(payment_info, reply_markup=create_base_keyboard())
            logger.info(f"Order {order.id} created and ready for payment")

        except Exception as e:
            logger.error(f"Error saving order to database: {str(e)}", exc_info=True)
            await message.answer(
                "❌ Произошла ошибка при сохранении заказа",
                reply_markup=create_base_keyboard()
            )
            await state.clear()
            return

    except Exception as e:
        logger.error(f"Error in process_delivery_address: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при сохранении адреса",
            reply_markup=create_base_keyboard()
        )
        await state.clear()

def register_delivery_handlers(dp: Dispatcher):
    """Регистрация обработчиков доставки"""
    try:
        logger.info("Registering delivery handlers")

        # Регистрируем обработчики состояний оформления доставки
        dp.message.register(process_delivery_checkout, F.text == "✅ Подтвердить заказ")
        dp.message.register(process_customer_name, ShopStates.WAITING_FOR_CUSTOMER_NAME)
        dp.message.register(process_customer_phone, ShopStates.WAITING_FOR_CUSTOMER_PHONE)
        dp.message.register(process_delivery_address, ShopStates.WAITING_FOR_DELIVERY_ADDRESS)

        logger.info("Delivery handlers registered successfully")

    except Exception as e:
        logger.error(f"Error registering delivery handlers: {str(e)}", exc_info=True)
        raise