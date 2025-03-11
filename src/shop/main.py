"""Shop module for the Telegram bot."""
import logging
import os
from datetime import datetime, timedelta
import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .database import get_db
from .models import Product
from .states import ShopStates
from .protected_handlers import (
    create_base_keyboard,
    shop_command_handler,
    category_handler,
    show_product_category,
    handle_photo_navigation
)
from src.receipt_processor.image_processor import process_image

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_moscow_time():
    """Returns the current time in Moscow (MSK)."""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)


async def process_cart_checkout(message: Message, state: FSMContext):
    """Начало оформления заказа"""
    try:
        user_id = message.from_user.id
        logger.info(f"Starting checkout process for user {user_id}")

        data = await state.get_data()
        cart = data.get('cart', {})

        if not cart:
            await message.answer(
                "🛒 Ваша корзина пуста. Добавьте товары для оформления заказа.",
                reply_markup=create_base_keyboard()
            )
            return

        # Показываем итоговую информацию о заказе и процессе оформления
        total_sum = sum(item['price'] * item['quantity'] for item in cart.values())
        order_info = "📋 Ваш заказ:\n\n"

        for product_id, item in cart.items():
            subtotal = item['price'] * item['quantity']
            order_info += (
                f"📦 {item['name']}\n"
                f"💰 {item['price']:,.2f}₽ x {item['quantity']} шт. = {subtotal:,.2f}₽\n\n"
            )

        order_info += f"\n💰 Итого к оплате: {total_sum:,.2f}₽"

        # Отправляем информацию о процессе оформления заказа
        await message.answer(
            f"{order_info}\n\n"
            "📝 Порядок оформления заказа:\n\n"
            "1️⃣ Сначала вам нужно будет указать данные для доставки:\n"
            "   - ФИО получателя\n"
            "   - Контактный телефон\n"
            "   - Адрес доставки\n\n"
            "2️⃣ После этого вы получите QR-код для оплаты\n\n"
            "3️⃣ Произведите оплату и сохраните электронный чек\n\n"
            "4️⃣ Отправьте чек в чат для проверки\n\n"
            "5️⃣ После успешной проверки чека статус заказа изменится на 'Оформлен'\n\n"
            "👤 Пожалуйста, введите ваше полное имя:"
        )

        await state.update_data(total_sum=total_sum, cart=cart)
        await state.set_state(ShopStates.WAITING_FOR_CUSTOMER_NAME)
        logger.info(f"Requesting customer name for user {user_id}")

    except Exception as e:
        logger.error(f"Error in process_cart_checkout: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при оформлении заказа. Попробуйте позже.",
            reply_markup=create_base_keyboard()
        )
        await state.clear()

async def process_customer_name(message: Message, state: FSMContext):
    """Обработка ФИО покупателя"""
    try:
        user_id = message.from_user.id
        customer_name = message.text.strip()
        logger.info(f"Processing customer name for user {user_id}: {customer_name}")

        if len(customer_name) < 2:
            await message.answer("⚠️ Пожалуйста, введите корректное ФИО")
            return

        await state.update_data(customer_name=customer_name)
        await message.answer(
            "📱 Введите ваш номер телефона для связи:\n"
            "Например: +7XXXXXXXXXX"
        )
        await state.set_state(ShopStates.WAITING_FOR_CUSTOMER_PHONE)
        logger.info(f"Customer name saved: {customer_name}, requesting phone for user {user_id}")

    except Exception as e:
        logger.error(f"Error in process_customer_name: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await state.clear()

async def process_customer_phone(message: Message, state: FSMContext):
    """Обработка телефона покупателя"""
    try:
        user_id = message.from_user.id
        phone = message.text.strip()
        logger.info(f"Processing phone for user {user_id}: {phone}")

        # Простая валидация телефона
        if not phone.replace('+', '').isdigit() or len(phone) < 10:
            await message.answer(
                "⚠️ Пожалуйста, введите корректный номер телефона\n"
                "Например: +7XXXXXXXXXX"
            )
            return

        await state.update_data(phone=phone)
        await message.answer(
            "📧 Введите ваш email для получения подтверждения заказа:"
        )
        await state.set_state(ShopStates.WAITING_FOR_CUSTOMER_EMAIL)
        logger.info(f"Phone saved: {phone}, requesting email for user {user_id}")

    except Exception as e:
        logger.error(f"Error in process_customer_phone: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await state.clear()

async def process_customer_email(message: Message, state: FSMContext):
    """Обработка email покупателя"""
    try:
        user_id = message.from_user.id
        email = message.text.strip().lower()
        logger.info(f"Processing email for user {user_id}: {email}")
        logger.info(f"Current state before processing: {await state.get_state()}")

        # Простая валидация email
        if '@' not in email or '.' not in email or len(email) < 5:
            await message.answer("⚠️ Пожалуйста, введите корректный email адрес")
            return

        await state.update_data(customer_email=email)
        logger.info(f"Email saved: {email}, updating state for user {user_id}")

        # Проверяем текущее состояние перед переходом к следующему
        current_state = await state.get_state()
        if current_state != ShopStates.WAITING_FOR_CUSTOMER_EMAIL.state:
            logger.error(f"Unexpected state after email input: {current_state}")
            return

        # Переходим к следующему шагу
        await state.set_state(ShopStates.WAITING_FOR_DELIVERY_ADDRESS)
        logger.info(f"State set to WAITING_FOR_DELIVERY_ADDRESS for user {user_id}")

        await message.answer(
            "📍 Введите адрес доставки:\n"
            "(улица, дом, квартира, город)"
        )

    except Exception as e:
        logger.error(f"Error in process_customer_email: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке email. Попробуйте позже.")

async def process_delivery_address(message: Message, state: FSMContext):
    """Обработка адреса доставки"""
    try:
        user_id = message.from_user.id
        address = message.text.strip()
        logger.info(f"Processing delivery address for user {user_id}: {address}")

        if len(address) < 10:
            await message.answer("⚠️ Пожалуйста, введите полный адрес доставки")
            return

        # Сохраняем адрес и получаем данные заказа
        await state.update_data(delivery_address=address)
        data = await state.get_data()
        total_sum = data.get('total_sum', 0)

        # Отправляем инструкции по оплате
        payment_message = (
            "💳 Порядок оплаты заказа:\n\n"
            f"Сумма к оплате: {total_sum:,.2f}₽\n\n"
            "1️⃣ Отсканируйте QR-код или перейдите по ссылке для оплаты:\n"
            "https://qr.nspk.ru/AS20006OKC648VO0845BQH1MD028D7B8?type=01&bank=100000000005&sum=5000&cur=RUB&crc=1443\n\n"
            "2️⃣ После оплаты сохраните электронный чек из банка\n\n"
            "3️⃣ Прикрепите сохраненный чек для проверки в этот чат\n\n"
            "4️⃣ Мы проверим чек и поменяем статус заказа на 'Оформлен'\n"
            "   и пришлем вам оповещение на указанный email\n\n"
            "⚠️ Важно: Заказ будет подтвержден только после успешной проверки чека"
        )

        # Переводим в состояние ожидания чека
        await state.set_state(ShopStates.WAITING_FOR_RECEIPT)
        current_state = await state.get_state()
        logger.info(f"Set state to WAITING_FOR_RECEIPT for user {user_id}, current state: {current_state}")

        # Отправляем сообщение с QR-кодом и инструкциями
        await message.answer(payment_message)
        logger.info(f"Payment instructions sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error in process_delivery_address: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await state.clear()

async def handle_text_in_receipt_state(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений в состоянии ожидания чека"""
    try:
        current_state = await state.get_state()
        logger.info(f"Handling text message in receipt state for user {message.from_user.id}")
        logger.info(f"Current state: {current_state}")

        if current_state == ShopStates.WAITING_FOR_RECEIPT.state:
            await message.answer(
                "❌ Пожалуйста, отправьте фотографию чека об оплате.\n"
                "Убедитесь, что все детали платежа хорошо видны на изображении."
            )
            logger.info(f"Sent reminder to upload receipt photo to user {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in handle_text_in_receipt_state: {str(e)}", exc_info=True)

async def process_payment_receipt(message: Message, state: FSMContext):
    """Обработка загруженного чека об оплате (фото или PDF)"""
    try:
        user_id = message.from_user.id
        logger.info(f"Получен чек об оплате от пользователя {user_id}")

        # Получаем файл (фото или документ)
        file = None
        file_path = None
        temp_file = None
        is_photo = False

        if message.photo:
            photo = message.photo[-1]
            file = await message.bot.get_file(photo.file_id)
            file_path = file.file_path
            is_photo = True
            logger.info(f"Получено фото чека: {file.file_id}")
        elif message.document and message.document.mime_type == 'application/pdf':
            file = await message.bot.get_file(message.document.file_id)
            file_path = file.file_path
            logger.info(f"Получен PDF документ: {file.file_id}")
        else:
            await message.answer(
                "❌ Пожалуйста, отправьте чек об оплате в виде фотографии или PDF-документа."
            )
            return

        # Показываем сообщение о начале обработки
        processing_msg = await message.answer("🔄 Проверяю чек об оплате...")

        try:
            # Скачиваем файл
            photo_bytes = await message.bot.download_file(file_path)
            logger.info("Файл успешно скачан")

            ext = '.jpg' if is_photo else '.pdf'
            temp_file = f"temp_{user_id}_{message.message_id}{ext}"

            with open(temp_file, 'wb') as f:
                f.write(photo_bytes.read())
            logger.info(f"Файл сохранен как: {temp_file}")

            # Получаем текущую дату (MSK)
            current_date = get_moscow_time().date()
            logger.info(f"Текущая дата (МСК): {current_date}")

            # Обработка чека
            success, receipt_date, receipt_path, message_text = process_image(temp_file, user_id)
            logger.info(f"Результат обработки чека: success={success}, receipt_date={receipt_date}, message={message_text}")

            if not success:
                logger.error(f"Ошибка при обработке чека: {message_text}")
                await message.answer(f"❌ {message_text}")
                return

            # Проверяем дату чека
            if receipt_date != current_date:
                logger.warning(f"Несовпадение дат: чек={receipt_date}, текущая={current_date}")
                await message.answer(
                    "❌ Дата в чеке не совпадает с датой оформления заказа.\n"
                    "Заказ не может быть принят."
                )
                return

            # Получаем данные о заказе
            data = await state.get_data()
            customer_name = data.get('customer_name', '')
            customer_email = data.get('customer_email', '')
            delivery_address = data.get('delivery_address', '')
            phone = data.get('phone', '')
            cart = data.get('cart', {})
            # expected_amount = data.get('total_sum') # Временно отключаем проверку суммы

            # Формируем текст для писем
            order_details = (
                f"🛍️ Новый заказ\n\n"
                f"👤 Клиент: {customer_name}\n"
                f"📱 Телефон: {phone}\n"
                f"📧 Email: {customer_email}\n"
                f"📍 Адрес доставки: {delivery_address}\n\n"
                f"📦 Товары в заказе:\n"
            )

            for product_id, item in cart.items():
                subtotal = item['price'] * item['quantity']
                order_details += (
                    f"- {item['name']}\n"
                    f"  {item['price']}₽ x {item['quantity']} шт. = {subtotal}₽\n"
                )

            # Отправляем уведомления с файлом чека
            admin_email = os.getenv('ADMIN_EMAIL', 'sale@introlaser.ru')

            # Отправляем администратору
            await send_email_notification(
                admin_email,
                "Новый заказ",
                order_details,
                receipt_path
            )
            logger.info(f"Отправлено уведомление о заказе на {admin_email}")

            # Отправляем клиенту
            client_message = (
                f"Здравствуйте, {customer_name}!\n\n"
                f"Ваш заказ успешно оформлен и оплачен.\n\n"
                f"📦 Детали заказа:\n"
                f"{order_details}\n\n"
                f"Мы свяжемся с вами для уточнения деталей доставки."
            )

            await send_email_notification(
                customer_email,
                "Подтверждение заказа",
                client_message,
                receipt_path
            )
            logger.info(f"Отправлено подтверждение заказа клиенту на {customer_email}")

            # Отправляем краткое подтверждение в телеграм
            await message.answer(
                "✅ Заказ успешно оформлен!\n"
                "Подтверждение отправлено на ваш email."
            )

            # Переводим заказ в статус "оплачен"
            await state.set_state(ShopStates.ORDER_PAID)
            logger.info(f"Заказ переведен в статус PAID для пользователя {user_id}")

        except Exception as e:
            logger.error(f"Ошибка при обработке чека: {str(e)}", exc_info=True)
            await message.answer(
                "❌ Произошла ошибка при проверке чека.\n"
                "Пожалуйста, попробуйте снова."
            )
        finally:
            # Удаляем временный файл и сообщение о процессе
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"Временный файл удален: {temp_file}")
            await processing_msg.delete()

    except Exception as e:
        logger.error(f"Общая ошибка в process_payment_receipt: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке чека.\n"
            "Пожалуйста, попробуйте снова."
        )
        await state.clear()

async def cart_handler(message: Message, state: FSMContext):
    """Обработчик корзины"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing cart for user {user_id}")

        data = await state.get_data()
        cart = data.get('cart', {})

        if not cart:
            await message.answer(
                "🛒 Ваша корзина пуста",
                reply_markup=create_base_keyboard()
            )
            return

        cart_text = "🛒 Ваша корзина:\n\n"
        total_sum = 0
        buttons = []

        db = get_db()
        for product_id, item in cart.items():
            product = db.query(Product).filter(Product.id == int(product_id)).first()
            if not product:
                continue

            subtotal = item['price'] * item['quantity']
            total_sum += subtotal

            cart_text += (
                f"📦 {item['name']}\n"
                f"💰 {item['price']:,.0f}₽ x {item['quantity']} шт. = {subtotal:,.0f}₽\n\n"
            )

            buttons.append([
                InlineKeyboardButton(text="➖", callback_data=f"cart_decrease_{product_id}"),
                InlineKeyboardButton(text=f"{item['quantity']} шт.", callback_data=f"cart_info_{product_id}"),
                InlineKeyboardButton(text="➕", callback_data=f"cart_increase_{product_id}")
            ])
            buttons.append([
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"cart_remove_{product_id}")
            ])

        cart_text += f"\n💰 Итого: {total_sum:,.0f}₽"

        buttons.append([
            InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear"),
            InlineKeyboardButton(text="💳 Оформить заказ", callback_data="cart_checkout")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(cart_text, reply_markup=keyboard)
        logger.info(f"Cart info sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error in cart_handler: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при отображении корзины",
            reply_markup=create_base_keyboard()
        )

async def process_cart_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка callback-ов корзины"""
    try:
        action = callback.data.split('_')[1]
        product_id = callback.data.split('_')[2] if len(callback.data.split('_')) > 2 else None

        user_data = await state.get_data()
        cart = user_data.get('cart', {})

        if action == "clear":
            await state.update_data(cart={})
            await callback.message.edit_text("🛒 Корзина очищена")
            await callback.answer("✅ Корзина очищена")
            return

        if action == "checkout":
            await callback.answer("⏳ Переходим к оформлению заказа")
            await process_cart_checkout(callback.message, state)
            return

        if not product_id or product_id not in cart:
            await callback.answer("❌ Товар не найден в корзине")
            return

        if action == "increase":
            cart[product_id]['quantity'] += 1
            await callback.answer(f"✅ Количество увеличено до {cart[product_id]['quantity']}")

        elif action == "decrease":
            if cart[product_id]['quantity'] > 1:
                cart[product_id]['quantity'] -= 1
                await callback.answer(f"✅ Количество уменьшено до {cart[product_id]['quantity']}")
            else:
                await callback.answer("❌ Нельзя уменьшить количество меньше 1")

        elif action == "remove":
            del cart[product_id]
            await callback.answer("✅ Товар удален из корзины")

        await state.update_data(cart=cart)

        if cart:
            await cart_handler(callback.message, state)
        else:
            await callback.message.edit_text("🛒 Корзина пуста")

    except Exception as e:
        logger.error(f"Error in process_cart_callback: {str(e)}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при обработке действия")

async def process_add_to_cart_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка добавления товара в корзину"""
    try:
        product_id = str(callback.data.split('_')[-1])
        logger.info(f"Processing add to cart callback for product {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == int(product_id)).first()

        if not product:
            await callback.answer("❌ Товар не найден")
            return

        data = await state.get_data()
        cart = data.get('cart', {})

        if product_id in cart:
            cart[product_id]['quantity'] += 1
        else:
            cart[product_id] = {
                'name': product.name,
                'price': float(product.price),
                'quantity': 1
            }

        await state.update_data(cart=cart)
        total_items = sum(item['quantity'] for item in cart.values())

        await callback.answer(
            f"✅ {product.name} добавлен в корзину (всего: {total_items} шт.)"
        )

    except Exception as e:
        logger.error(f"Error in process_add_to_cart_callback: {str(e)}", exc_info=True)
        await callback.answer("❌ Ошибка при добавлении товара в корзину")

async def register_shop_handlers(dp: Dispatcher):
    """Регистрация обработчиков для магазина"""
    try:
        logger.info("Starting shop handlers registration")

        # 1. Регистрируем обработчики состояний оформления заказа (строго в таком порядке)
        dp.message.register(process_customer_name, ShopStates.WAITING_FOR_CUSTOMER_NAME)
        dp.message.register(process_customer_phone, ShopStates.WAITING_FOR_CUSTOMER_PHONE)
        dp.message.register(process_customer_email, ShopStates.WAITING_FOR_CUSTOMER_EMAIL)
        dp.message.register(process_delivery_address, ShopStates.WAITING_FOR_DELIVERY_ADDRESS)
        dp.message.register(handle_text_in_receipt_state, F.text, ShopStates.WAITING_FOR_RECEIPT)
        dp.message.register(process_payment_receipt, F.photo | (F.document.mime_type == 'application/pdf'), ShopStates.WAITING_FOR_RECEIPT)

        # 2. Регистрируем обработчики основных команд магазина
        dp.message.register(shop_command_handler, Command("shop"))
        dp.message.register(shop_command_handler, F.text == "⬅️ Назад в магазин")
        dp.message.register(category_handler, F.text.in_(["💆‍♀️ Косметология", "🔧 Электроника"]))
        dp.message.register(cart_handler, F.text == "🛒 Корзина")

        # 3. Регистрируем callback-обработчики
        dp.callback_query.register(process_cart_callback, F.data.startswith("cart_"))
        dp.callback_query.register(process_add_to_cart_callback, F.data.startswith("add_to_cart_"))
        dp.callback_query.register(handle_photo_navigation, F.data.startswith("photo_preview_"))
        dp.callback_query.register(
            handle_photo_navigation,
            F.data.startswith(("next_photo_", "prev_photo_", "photo_dot_"))
        )

        logger.info("All shop handlers registered successfully")

    except Exception as e:
        logger.error(f"Error registering shop handlers: {str(e)}")
        raise

async def handle_invalid_input(message: Message, state: FSMContext):
    """Обработчик неправильных команд и текстовых сообщений"""
    try:
        user_id = message.from_user.id
        current_state = await state.get_state()
        logger.info(f"Invalid input handler called for user {user_id}")
        logger.info(f"Current state: {current_state}")

        # Пропускаем обработку для всех состояний оформления заказа
        if current_state in [
            ShopStates.WAITING_FOR_CUSTOMER_NAME.state,
            ShopStates.WAITING_FOR_CUSTOMER_PHONE.state,
            ShopStates.WAITING_FOR_CUSTOMER_EMAIL.state,
            ShopStates.WAITING_FOR_DELIVERY_ADDRESS.state,
            ShopStates.WAITING_FOR_RECEIPT.state
        ]:
            logger.info(f"Skipping invalid input handler for shop state: {current_state}")
            return

        logger.info(f"Processing invalid input from user {user_id}: {message.text}")

        help_message = (
            "⚠️ Пожалуйста, выберите команду из меню или используйте:\n\n"
            "🛍 Кнопки в меню магазина для покупок\n"
            "📝 Команду /o для анализа отзыва\n"
            "❓ Команду /start для начала работы"
        )

        await message.answer(help_message, reply_markup=create_base_keyboard())
        logger.info(f"Sent help message to user {user_id}")

    except Exception as e:
        logger.error(f"Error in handle_invalid_input: {str(e)}", exc_info=True)
        await message.answer("Пожалуйста, используйте команду из списка меню или /start")


async def initialize_test_products():
    """Инициализация тестовых товаров"""
    try:
        logger.info("Starting test products initialization")
        db = get_db()

        # Проверяем, есть ли уже товары
        existing_products = db.query(Product).count()
        if existing_products > 0:
            logger.info("Products already exist, skipping initialization")
            return

        # Товары для категории Косметология
        cosmetics_products = [
            {
                "name": "Крем для лица омолаживающий",
                "description": "Интенсивный омолаживающий крем с гиалуроновой кислотой",
                "price": 2500.00,
                "category": "cosmetics",
                "specifications": "Объем: 50мл, Производство: Россия",
                "available": True
            },
            {
                "name": "Маска для волос питательная",
                "description": "Питательная маска для всех типов волос с кератином",
                "price": 1800.00,
                "category": "cosmetics",
                "specifications": "Объем: 200мл, Производство: Франция",
                "available": True
            }
        ]

        # Товары для категории Электроника
        electronics_products = [
            {
                "name": "Фен профессиональный",
                "description": "Профессиональный фен с ионизацией и 3 режимами работы",
                "price": 5900.00,
                "category": "electronics",
                "specifications": "Мощность: 2200Вт, 3 скорости, 2 насадки",
                "available": True
            },
            {
                "name": "Массажер для лица",
                "description": "Электрический массажер для ухода за кожей лица",
                "price": 3200.00,
                "category": "electronics",
                "specifications": "5 режимов работы, Аккумулятор: 2000mAh",
                "available": True
            }
        ]

        # Добавляем товары в базу данных
        for product_data in cosmetics_products + electronics_products:
            product = Product(**product_data)
            db.add(product)
            logger.info(f"Added product: {product_data['name']}")

        db.commit()
        logger.info("Test products initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing test products: {str(e)}", exc_info=True)
        db.rollback()
        raise

async def send_email_notification(recipient, subject, body, attachment_path):
    #Implementation for sending email with attachment
    pass