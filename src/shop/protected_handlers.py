"""Protected handlers module for the shop.
WARNING: This file contains verified working code.
DO NOT MODIFY these handlers without explicit permission.
Last verified: 24.02.2025
"""

import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .database import get_db
from .models import Product
from .states import ShopStates

logger = logging.getLogger(__name__)

def create_base_keyboard() -> ReplyKeyboardMarkup:
    """Создание базовой клавиатуры магазина
    WARNING: This is a protected function. DO NOT MODIFY.
    Last verified: 24.02.2025
    """
    try:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="💆‍♀️ Косметология"),
                    KeyboardButton(text="🔧 Электроника")
                ],
                [KeyboardButton(text="🛒 Корзина")],
                [KeyboardButton(text="❓ Задать вопрос")]
            ],
            resize_keyboard=True,
            persistent=True
        )
        logger.info("Base keyboard created successfully")
        return keyboard
    except Exception as e:
        logger.error(f"Error creating base keyboard: {str(e)}", exc_info=True)
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🛒 Корзина")]],
            resize_keyboard=True
        )

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
            # Получаем информацию о товаре из базы данных
            product = db.query(Product).filter(Product.id == int(product_id)).first()
            if not product:
                continue

            subtotal = item['price'] * item['quantity']
            total_sum += subtotal

            # Добавляем информацию о товаре
            cart_text += (
                f"📦 {item['name']}\n"
                f"💰 {item['price']:,.0f}₽ x {item['quantity']} шт. = {subtotal:,.0f}₽\n\n"
            )

            # Создаем кнопки управления для товара
            buttons.append([
                InlineKeyboardButton(text="➖", callback_data=f"cart_decrease_{product_id}"),
                InlineKeyboardButton(text=f"{item['quantity']} шт.", callback_data=f"cart_info_{product_id}"),
                InlineKeyboardButton(text="➕", callback_data=f"cart_increase_{product_id}")
            ])
            buttons.append([
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"cart_remove_{product_id}")
            ])

        cart_text += f"\n💰 Итого: {total_sum:,.0f}₽"

        # Добавляем кнопки действий с корзиной
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
            await process_cart_checkout(callback.message, state) # Assuming process_cart_checkout exists elsewhere
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

async def shop_command_handler(message: Message, state: FSMContext):
    """Обработчик команды магазина
    WARNING: This is a protected handler. DO NOT MODIFY.
    Last verified: 24.02.2025
    """
    try:
        user_id = message.from_user.id
        logger.info(f"Shop command handler called for user {user_id}")

        await state.clear()
        logger.info(f"State cleared for user {user_id}")

        keyboard = create_base_keyboard()

        welcome_message = (
            "🏪 Добро пожаловать в магазин!\n\n"
            "Выберите категорию товаров:\n"
            "💆‍♀️ Косметология - товары для красоты и здоровья\n"
            "🔧 Электроника - электронные устройства и аксессуары\n\n"
            "Используйте кнопку 🛒 Корзина для просмотра выбранных товаров"
        )

        await message.answer(welcome_message, reply_markup=keyboard)
        logger.info(f"Welcome message sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error in shop_command_handler: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при открытии магазина. Попробуйте позже.",
            reply_markup=create_base_keyboard()
        )

async def category_handler(message: Message, state: FSMContext):
    """Обработчик выбора категории
    WARNING: This is a protected handler. DO NOT MODIFY.
    Last verified: 24.02.2025
    """
    try:
        user_id = message.from_user.id
        logger.info(f"Category handler called for user {user_id} with message: {message.text}")

        category = None
        if message.text == "💆‍♀️ Косметология":
            category = "cosmetics"
            logger.info(f"User {user_id} selected Косметология category")
        elif message.text == "🔧 Электроника":
            category = "electronics"
            logger.info(f"User {user_id} selected Электроника category")

        if category:
            await show_product_category(message, state, category)
        else:
            logger.warning(f"Unknown category message: {message.text} from user {user_id}")

    except Exception as e:
        logger.error(f"Error in category_handler: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при получении списка товаров",
            reply_markup=create_base_keyboard()
        )

async def show_product_category(message: Message, state: FSMContext, category: str):
    """Показать товары в выбранной категории"""
    try:
        user_id = message.from_user.id
        logger.info(f"Showing products for category {category} to user {user_id}")

        db = get_db()
        products = db.query(Product).filter(
            Product.category == category,
            Product.available == True
        ).all()

        logger.info(f"Found {len(products)} products in category {category}")

        if not products:
            await message.answer(
                "😔 В данной категории пока нет товаров",
                reply_markup=create_base_keyboard()
            )
            return

        for product in products:
            # Получаем все фотографии товара, отсортированные по порядку
            photos = sorted(product.photos, key=lambda x: x.sort_order)

            # Создаем описание товара
            description = (
                f"📦 {product.name}\n"
                f"💰 Цена: {product.price:,.2f} руб.\n\n"
                f"📝 Описание: {product.description}\n"
                f"⚙️ Характеристики: {product.specifications}"
            )

            # Отправляем первую фотографию с описанием
            if photos:
                keyboard_buttons = []

                # Создаем ряд превью фотографий
                if len(photos) > 1:
                    previews = []
                    for i, photo in enumerate(photos):
                        # Создаем кнопку с callback_data для каждого превью
                        previews.append(
                            InlineKeyboardButton(
                                text=f"📷 {i+1}",  # Номер фото в виде emoji
                                callback_data=f"photo_preview_{product.id}_{i}"
                            )
                        )
                    keyboard_buttons.append(previews)

                # Добавляем кнопку корзины
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="🛒 Добавить в корзину",
                        callback_data=f"add_to_cart_{product.id}"
                    )
                ])

                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

                await message.answer_photo(
                    photo=photos[0].photo_url,
                    caption=description,
                    reply_markup=keyboard,
                    width=400,  # Размер основного фото
                    height=300
                )
            else:
                await message.answer(description)

            logger.info(f"Sent product {product.id} info to user {user_id}")

        # В конце показываем основную клавиатуру
        await message.answer(
            "Выберите действие:",
            reply_markup=create_base_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in show_product_category: {str(e)}", exc_info=True)
        await message.answer(
            "Произошла ошибка при отображении товаров",
            reply_markup=create_base_keyboard()
        )

async def handle_photo_navigation(callback: CallbackQuery, state: FSMContext):
    """Обработчик навигации по фотографиям товара"""
    try:
        # Добавляем подробное логирование
        logger.info(f"Handling photo navigation callback: {callback.data}")

        # Парсим данные из callback
        parts = callback.data.split('_')
        if len(parts) < 4:
            logger.error(f"Invalid callback data format: {callback.data}")
            await callback.answer("❌ Неверный формат данных")
            return

        action = parts[0]  # photo
        preview = parts[1]  # preview
        product_id = int(parts[2])
        new_index = int(parts[3])

        logger.info(f"Preview navigation: product_id={product_id}, target_index={new_index}")

        # Получаем информацию о товаре
        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            logger.error(f"Product not found: {product_id}")
            await callback.answer("❌ Товар не найден")
            return

        # Получаем отсортированные фотографии
        photos = sorted(product.photos, key=lambda x: x.sort_order)
        if not photos:
            logger.error(f"No photos found for product: {product_id}")
            await callback.answer("❌ Фотографии не найдены")
            return

        logger.info(f"Found {len(photos)} photos for product {product_id}")

        # Проверяем валидность индекса
        if new_index < 0 or new_index >= len(photos):
            logger.error(f"Invalid photo index: {new_index}")
            await callback.answer("❌ Неверный индекс фото")
            return

        # Создаем клавиатуру с превью и кнопкой корзины
        keyboard_buttons = []

        # Создаем ряд превью фотографий
        if len(photos) > 1:
            previews = []
            for i, photo in enumerate(photos):
                # Создаем кнопку с callback_data для каждого превью
                previews.append(
                    InlineKeyboardButton(
                        text=f"📷 {i+1}",  # Номер фото в виде emoji
                        callback_data=f"photo_preview_{product_id}_{i}"
                    )
                )
            keyboard_buttons.append(previews)

        # Добавляем кнопку корзины
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="🛒 Добавить в корзину",
                callback_data=f"add_to_cart_{product.id}"
            )
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        # Формируем описание
        description = (
            f"📦 {product.name}\n"
            f"💰 Цена: {product.price:,.2f} руб.\n\n"
            f"📝 Описание: {product.description}\n"
            f"⚙️ Характеристики: {product.specifications}"
        )

        try:
            # Обновляем фотографию
            await callback.message.edit_media(
                media=InputMediaPhoto(
                    media=photos[new_index].photo_url,
                    caption=description
                ),
                reply_markup=keyboard
            )
            logger.info(f"Successfully updated photo to index {new_index}")
        except Exception as e:
            logger.error(f"Error updating media: {str(e)}", exc_info=True)
            await callback.answer("❌ Ошибка при обновлении фото")
            return

        await callback.answer()
        logger.info("Photo navigation completed successfully")

    except Exception as e:
        logger.error(f"Error in handle_photo_navigation: {str(e)}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при навигации по фото")

async def process_cart_checkout(message:Message, state: FSMContext):
    # Placeholder for checkout logic.  Implementation details omitted as not provided in the edited snippet
    await message.answer("Checkout functionality not yet implemented.")
    await state.clear()