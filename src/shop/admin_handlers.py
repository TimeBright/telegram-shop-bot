"""Admin handlers module for the shop."""
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .states import ShopStates
from .database import get_db
from .models import Product, Order

# Настройка логирования
logger = logging.getLogger(__name__)

async def handle_add_product_name(message: Message, state: FSMContext):
    """Обработчик добавления названия нового товара"""
    try:
        await state.update_data(new_product_name=message.text)
        await message.answer("Введите описание товара:")
        await state.set_state(ShopStates.WAITING_FOR_PRODUCT_DESCRIPTION)
    except Exception as e:
        logger.error(f"Error in handle_add_product_name: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при добавлении названия товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def handle_add_product_description(message: Message, state: FSMContext):
    """Обработчик добавления описания нового товара"""
    try:
        await state.update_data(new_product_description=message.text)
        await message.answer("Введите цену товара (только число):")
        await state.set_state(ShopStates.WAITING_FOR_PRODUCT_PRICE)
    except Exception as e:
        logger.error(f"Error in handle_add_product_description: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при добавлении описания товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def handle_add_product_price(message: Message, state: FSMContext):
    """Обработчик добавления цены нового товара"""
    try:
        try:
            price = float(message.text)
            if price <= 0:
                raise ValueError("Цена должна быть положительным числом")
        except ValueError:
            await message.answer("❌ Пожалуйста, введите корректное число для цены")
            return

        await state.update_data(new_product_price=price)

        # Создаем клавиатуру для выбора категории
        category_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="💆‍♀️ Косметология"),
                    KeyboardButton(text="🔧 Электроника")
                ],
                [KeyboardButton(text="🔙 Отменить добавление")]
            ],
            resize_keyboard=True,
            persistent=True
        )

        await message.answer(
            "Выберите категорию товара:",
            reply_markup=category_keyboard
        )
        await state.set_state(ShopStates.WAITING_FOR_PRODUCT_CATEGORY)
    except Exception as e:
        logger.error(f"Error in handle_add_product_price: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при добавлении цены товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def handle_add_product_category(message: Message, state: FSMContext):
    """Обработчик добавления категории нового товара"""
    try:
        if message.text == "🔙 Отменить добавление":
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "Добавление товара отменено",
                reply_markup=create_product_management_keyboard()
            )
            return

        category = None
        if message.text == "💆‍♀️ Косметология":
            category = "cosmetics"
        elif message.text == "🔧 Электроника":
            category = "electronics"
        else:
            await message.answer("❌ Пожалуйста, выберите категорию из списка")
            return

        await state.update_data(new_product_category=category)
        await message.answer("Введите характеристики товара:")
        await state.set_state(ShopStates.WAITING_FOR_PRODUCT_SPECIFICATIONS)
    except Exception as e:
        logger.error(f"Error in handle_add_product_category: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при выборе категории",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def handle_add_product_specifications(message: Message, state: FSMContext):
    """Обработчик добавления характеристик нового товара"""
    try:
        user_data = await state.get_data()

        # Создаем новый товар
        new_product = Product(
            name=user_data['new_product_name'],
            description=user_data['new_product_description'],
            price=user_data['new_product_price'],
            category=user_data['new_product_category'],
            specifications=message.text,
            available=True
        )

        db = get_db()
        db.add(new_product)
        db.commit()

        await message.answer(
            "✅ Товар успешно добавлен!",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in handle_add_product_specifications: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при добавлении товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

# Настройка клавиатуры админ-панели
def create_admin_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры для админ-панели"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📦 Управление товарами"),
                KeyboardButton(text="📋 Заказы")
            ],
            [
                KeyboardButton(text="❓ Вопросы"),
                KeyboardButton(text="📊 Статистика")
            ],
            [KeyboardButton(text="🔙 Выход из админ-панели")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

def create_product_management_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры для управления товарами"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Добавить товар"),
                KeyboardButton(text="📝 Редактировать товар")
            ],
            [
                KeyboardButton(text="❌ Удалить товар"),
                KeyboardButton(text="📋 Список товаров")
            ],
            [KeyboardButton(text="🔙 Назад в админ-меню")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

async def admin_start(message: Message, state: FSMContext):
    """Обработчик команды /admin"""
    try:
        user_id = message.from_user.id
        logger.info(f"Admin panel accessed by user {user_id}")

        await message.answer(
            "🔐 Для доступа к панели администратора введите код авторизации:"
        )
        await state.set_state(ShopStates.WAITING_FOR_ADMIN_AUTH_CODE)
        logger.info(f"Waiting for auth code from user {user_id}")

    except Exception as e:
        logger.error(f"Error in admin_start: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла ошибка при доступе к админ-панели")

async def check_auth_code(message: Message, state: FSMContext):
    """Проверка кода авторизации администратора"""
    try:
        user_id = message.from_user.id
        auth_code = message.text

        # TODO: Заменить на безопасную проверку из базы данных
        if auth_code == "admin123":  # Временный код для тестирования
            logger.info(f"Admin authentication successful for user {user_id}")

            await message.answer(
                "✅ Авторизация успешна!\n\n"
                "Добро пожаловать в панель администратора.\n"
                "Выберите нужный раздел:",
                reply_markup=create_admin_keyboard()
            )
            await state.set_state(ShopStates.ADMIN_MENU)

        else:
            logger.warning(f"Invalid auth code attempt from user {user_id}")
            await message.answer(
                "❌ Неверный код авторизации.\n"
                "Попробуйте еще раз или используйте /start для возврата в главное меню"
            )
            await state.clear()

    except Exception as e:
        logger.error(f"Error in check_auth_code: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при проверке кода.\n"
            "Используйте /start для возврата в главное меню"
        )
        await state.clear()

async def handle_admin_menu(message: Message, state: FSMContext):
    """Обработчик меню админ-панели"""
    try:
        user_id = message.from_user.id
        logger.info(f"Admin menu selection from user {user_id}: {message.text}")

        current_state = await state.get_state()
        if current_state != ShopStates.ADMIN_MENU.state:
            logger.warning(f"Invalid state for admin menu: {current_state}")
            return

        if message.text == "🔙 Выход из админ-панели":
            await state.clear()
            await message.answer(
                "👋 Вы вышли из админ-панели",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="/start")]],
                    resize_keyboard=True
                )
            )
            return

        # Обработка раздела управления товарами
        if message.text == "📦 Управление товарами":
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "📦 Управление товарами\n\n"
                "Выберите действие:",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Обработка других пунктов меню
        menu_responses = {
            "📋 Заказы": "Список последних заказов:",
            "❓ Вопросы": "Список вопросов от пользователей:",
            "📊 Статистика": "Статистика магазина:"
        }

        response = menu_responses.get(
            message.text,
            "⚠️ Пожалуйста, используйте кнопки меню"
        )
        await message.answer(response, reply_markup=create_admin_keyboard())

    except Exception as e:
        logger.error(f"Error in handle_admin_menu: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке команды",
            reply_markup=create_admin_keyboard()
        )

async def handle_product_management(message: Message, state: FSMContext):
    """Обработчик меню управления товарами"""
    try:
        user_id = message.from_user.id
        logger.info(f"Product management action from user {user_id}: {message.text}")

        current_state = await state.get_state()
        if current_state != ShopStates.ADMIN_PRODUCTS.state:
            logger.warning(f"Invalid state for product management: {current_state}")
            return

        if message.text == "🔙 Назад в админ-меню":
            await state.set_state(ShopStates.ADMIN_MENU)
            await message.answer(
                "Выберите раздел:",
                reply_markup=create_admin_keyboard()
            )
            return

        # Обработка действий с товарами
        action_handlers = {
            "➕ Добавить товар": (
                ShopStates.WAITING_FOR_PRODUCT_NAME,
                "Введите название нового товара:"
            ),
            "📝 Редактировать товар": (
                ShopStates.EDITING_PRODUCT,
                show_products_for_editing
            ),
            "❌ Удалить товар": (
                ShopStates.WAITING_FOR_PRODUCT_ID_TO_DELETE,
                show_products_for_deletion
            ),
            "📋 Список товаров": (None, show_products_list)
        }

        if message.text in action_handlers:
            next_state, handler = action_handlers[message.text]
            if next_state:
                await state.set_state(next_state)

            if callable(handler):
                await handler(message)
            else:
                await message.answer(handler)

            logger.info(f"Product management state set to {next_state} for user {user_id}")
        else:
            await message.answer(
                "⚠️ Выберите действие из меню",
                reply_markup=create_product_management_keyboard()
            )

    except Exception as e:
        logger.error(f"Error in handle_product_management: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при управлении товарами",
            reply_markup=create_product_management_keyboard()
        )

async def show_products_for_editing(message: Message):
    """Показать список товаров для редактирования"""
    try:
        db = get_db()
        products = db.query(Product).all()

        if not products:
            await message.answer(
                "❌ В базе данных нет товаров для редактирования",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Создаем клавиатуру со списком товаров
        product_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=f"ID:{product.id} - {product.name}")]
                for product in products
            ] + [[KeyboardButton(text="🔙 Назад к управлению товарами")]],
            resize_keyboard=True,
            persistent=True
        )

        await message.answer(
            "Выберите товар для редактирования:",
            reply_markup=product_keyboard
        )

    except Exception as e:
        logger.error(f"Error in show_products_for_editing: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при получении списка товаров",
            reply_markup=create_product_management_keyboard()
        )

async def show_products_list(message: Message):
    """Показать список всех товаров"""
    try:
        db = get_db()
        products = db.query(Product).all()

        if not products:
            await message.answer(
                "📋 Список товаров пуст",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Формируем текстовый список товаров
        products_text = "📋 Список товаров:\n\n"
        for product in products:
            products_text += (
                f"📦 {product.name}\n"
                f"ID: {product.id}\n"
                f"💰 Цена: {product.price:,.2f} руб.\n"
                f"📝 Описание: {product.description}\n"
                f"⚙️ Характеристики: {product.specifications}\n"
                f"{'✅ Доступен' if product.available else '❌ Недоступен'}\n\n"
            )

        await message.answer(
            products_text,
            reply_markup=create_product_management_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in show_products_list: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при получении списка товаров",
            reply_markup=create_product_management_keyboard()
        )

async def handle_product_editing(message: Message, state: FSMContext):
    """Обработчик редактирования товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Starting product editing for user {user_id}, message: {message.text}")

        if message.text == "🔙 Назад к управлению товарами":
            logger.info(f"User {user_id} returning to product management")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "Выберите действие:",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Проверяем, содержит ли сообщение ID товара
        if message.text.startswith(("📝", "💰", "📋", "⚙️", "✅")):
            # Это команда редактирования, передаем её в handle_edit_field
            await handle_edit_field(message, state)
            return

        if "ID:" not in message.text:
            logger.warning(f"Invalid product selection format from user {user_id}: {message.text}")
            await message.answer(
                "⚠️ Пожалуйста, выберите товар из списка",
                reply_markup=create_product_management_keyboard()
            )
            return

        try:
            # Извлекаем ID товара (формат "ID:X - Название")
            product_id = int(message.text.split("ID:")[1].split("-")[0].strip())
            logger.info(f"Extracted product ID: {product_id} for editing")

            # Получаем товар из базы данных
            db = get_db()
            product = db.query(Product).filter(Product.id == product_id).first()
            logger.info(f"Retrieved product from database: {product.name if product else 'Not found'}")

            if not product:
                logger.warning(f"Product with ID {product_id} not found in database")
                await message.answer(
                    "❌ Товар не найден",
                    reply_markup=create_product_management_keyboard()
                )
                return

            # Сохраняем ID товара в состоянии
            await state.update_data(editing_product_id=product_id)
            logger.info(f"Saved product ID {product_id} in state for user {user_id}")

            # Создаем клавиатуру для редактирования
            edit_keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text="📝 Изменить название"),
                        KeyboardButton(text="💰 Изменить цену")
                    ],
                    [
                        KeyboardButton(text="📋 Изменить описание"),
                        KeyboardButton(text="⚙️ Изменить характеристики")
                    ],
                    [
                        KeyboardButton(text="✅ Изменить доступность"),
                        KeyboardButton(text="🔙 Назад к списку товаров")
                    ]
                ],
                resize_keyboard=True,
                persistent=True
            )

            # Показываем информацию о товаре и опции редактирования
            product_info = (
                f"📦 Текущие данные товара:\n\n"
                f"Название: {product.name}\n"
                f"Цена: {product.price:,.2f} руб.\n"
                f"Описание: {product.description}\n"
                f"Характеристики: {product.specifications}\n"
                f"Доступность: {'✅ Доступен' if product.available else '❌ Недоступен'}\n\n"
                f"Выберите, что хотите изменить:"
            )

            await message.answer(product_info, reply_markup=edit_keyboard)
            logger.info(f"Sent product editing menu for product {product_id} to user {user_id}")

        except (ValueError, IndexError) as e:
            logger.error(f"Error extracting product ID: {str(e)}, message: {message.text}")
            await message.answer(
                "❌ Ошибка при определении ID товара",
                reply_markup=create_product_management_keyboard()
            )
            return

    except Exception as e:
        logger.error(f"Error in handle_product_editing: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при редактировании товара",
            reply_markup=create_product_management_keyboard()
        )

async def handle_edit_field(message: Message, state: FSMContext):
    """Обработчик редактирования полей товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Starting edit field handler for user {user_id}, message: {message.text}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        if not product_id:
            logger.error(f"No product_id found in state for user {user_id}")
            await message.answer(
                "❌ Ошибка: товар не выбран",
                reply_markup=create_product_management_keyboard()
            )
            return

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()
        logger.info(f"Retrieved product from database: {product.name if product else 'Not found'}")

        if not product:
            logger.error(f"Product with ID {product_id} not found in database")
            await message.answer(
                "❌ Товар не найден",
                reply_markup=create_product_management_keyboard()
            )
            return

        if message.text == "🔙 Назад к списку товаров":
            logger.info(f"User {user_id} returning to product list")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "Выберите действие:",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Определяем, какое поле редактируем и устанавливаем соответствующее состояние
        field_states = {
            "📝 Изменить название": ShopStates.WAITING_FOR_NEW_PRODUCT_NAME,
            "💰 Изменить цену": ShopStates.WAITING_FOR_NEW_PRODUCT_PRICE,
            "📋 Изменить описание": ShopStates.WAITING_FOR_NEW_PRODUCT_DESCRIPTION,
            "⚙️ Изменить характеристики": ShopStates.WAITING_FOR_NEW_PRODUCT_SPECS,
            "✅ Изменить доступность": None  # Обрабатываем сразу
        }

        if message.text == "✅ Изменить доступность":
            logger.info(f"Changing availability for product {product_id}")
            # Меняем доступность на противоположную
            old_status = product.available
            product.available = not product.available
            try:
                db.commit()
                logger.info(f"Successfully changed product {product_id} availability from {old_status} to {product.available}")
                status = "✅ доступен" if product.available else "❌ недоступен"
                await message.answer(
                    f"Статус товара изменен. Теперь товар {status}",
                    reply_markup=create_product_management_keyboard()
                )
                await state.set_state(ShopStates.ADMIN_PRODUCTS)
            except Exception as e:
                logger.error(f"Failed to update product availability: {str(e)}", exc_info=True)
                db.rollback()
                await message.answer(
                    "❌ Произошла ошибка при изменении доступности товара",
                    reply_markup=create_product_management_keyboard()
                )
            return

        next_state = field_states.get(message.text)
        if next_state:
            logger.info(f"Setting state to {next_state} for user {user_id}")
            await state.set_state(next_state)
            field_prompts = {
                ShopStates.WAITING_FOR_NEW_PRODUCT_NAME: "Введите новое название товара:",
                ShopStates.WAITING_FOR_NEW_PRODUCT_PRICE: "Введите новую цену товара (только число):",
                ShopStates.WAITING_FOR_NEW_PRODUCT_DESCRIPTION: "Введите новое описание товара:",
                ShopStates.WAITING_FOR_NEW_PRODUCT_SPECS: "Введите новые характеристики товара:"
            }
            await message.answer(field_prompts[next_state])
        else:
            logger.warning(f"Unknown action selected: {message.text}")
            await message.answer(
                "⚠️ Выберите действие из меню",
                reply_markup=create_product_management_keyboard()
            )

    except Exception as e:
        logger.error(f"Error in handle_edit_field: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при редактировании товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_name(message: Message, state: FSMContext):
    """Обработчик нового названия товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product name for user {user_id}: {message.text}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_name = product.name
        product.name = message.text
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} name from '{old_name}' to '{message.text}'")
            await message.answer(
                f"✅ Название товара успешно изменено на:\n{message.text}",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product name: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении нового названия",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_name: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении названия",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_price(message: Message, state: FSMContext):
    """Обработчик новой цены товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product price for user {user_id}: {message.text}")

        try:
            new_price = float(message.text)
            if new_price <= 0:
                raise ValueError("Цена должна быть положительным числом")
        except ValueError as e:
            logger.warning(f"Invalid price value: {message.text}")
            await message.answer(
                "❌ Пожалуйста, введите корректное число для цены",
                reply_markup=create_product_management_keyboard()
            )
            return

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_price = product.price
        product.price = new_price
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} price from {old_price} to {new_price}")
            await message.answer(
                f"✅ Цена товара успешно изменена на: {new_price:,.2f} руб.",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product price: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении новой цены",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_price: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении цены",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_description(message: Message, state: FSMContext):
    """Обработчик нового описания товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product description for user {user_id}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_description = product.description
        product.description = message.text
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} description")
            await message.answer(
                f"✅ Описание товара успешно изменено на:\n{message.text}",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product description: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении нового описания",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_description: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении описания",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_specifications(message: Message, state: FSMContext):
    """Обработчик новых характеристик товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product specifications for user {user_id}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_specs = product.specifications
        product.specifications = message.text
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} specifications")
            await message.answer(
                f"✅ Характеристики товара успешно изменены на:\n{message.text}",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product specifications: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении новых характеристик",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_specifications: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении характеристик",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def show_products_for_deletion(message: Message):
    """Показать список товаров для удаления"""
    try:
        db = get_db()
        products = db.query(Product).all()

        if not products:
            await message.answer(                "❌ В базе данных нет товаров для удаления",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Создаем клавиатуру со списком товаров
        product_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=f"❌ {product.name} (ID: {product.id})")]
                for product in products
            ] + [[KeyboardButton(text="🔙 Назад к управлению товарами")]],
            resize_keyboard=True,
            persistent=True
        )

        await message.answer(
            "⚠️ Выберите товар для удаления:\n"
            "(это действие нельзя будет отменить)",
            reply_markup=product_keyboard
        )

    except Exception as e:
        logger.error(f"Error in show_products_for_deletion: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при получении списка товаров",
            reply_markup=create_product_management_keyboard()
        )

async def handle_product_deletion(message: Message, state: FSMContext):
    """Обработчик удаления товара"""
    try:
        if message.text == "🔙 Назад к управлению товарами":
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "Выберите действие:",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Извлекаем ID товара из текста кнопки
        if not message.text.startswith("❌ "):
            await message.answer(
                "⚠️ Пожалуйста, выберите товар из списка",
                reply_markup=create_product_management_keyboard()
            )
            return

        try:
            product_id = int(message.text.split("ID: ")[-1].rstrip(")"))
        except (ValueError, IndexError):
            await message.answer(
                "❌ Ошибка при определении ID товара",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Получаем и удаляем товар из базы данных
        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            await message.answer(
                "❌ Товар не найден",
                reply_markup=create_product_management_keyboard()
            )
            return

        product_name = product.name
        db.delete(product)
        db.commit()

        await message.answer(
            f"✅ Товар '{product_name}' успешно удален",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in handle_product_deletion: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при удалении товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def register_admin_handlers(dp: Dispatcher):
    """Регистрация обработчиков админ-панели"""
    try:
        logger.info("Starting admin handlers registration")

        # Регистрация команды /admin и авторизации
        dp.message.register(admin_start, Command("admin"))
        dp.message.register(check_auth_code, ShopStates.WAITING_FOR_ADMIN_AUTH_CODE)

        # Регистрация обработчиков меню
        dp.message.register(handle_admin_menu, ShopStates.ADMIN_MENU)
        dp.message.register(handle_product_management, ShopStates.ADMIN_PRODUCTS)

        # Регистрация обработчиков добавления товара
        dp.message.register(handle_add_product_name, ShopStates.WAITING_FOR_PRODUCT_NAME)
        dp.message.register(handle_add_product_description, ShopStates.WAITING_FOR_PRODUCT_DESCRIPTION)
        dp.message.register(handle_add_product_price, ShopStates.WAITING_FOR_PRODUCT_PRICE)
        dp.message.register(handle_add_product_category, ShopStates.WAITING_FOR_PRODUCT_CATEGORY)
        dp.message.register(handle_add_product_specifications, ShopStates.WAITING_FOR_PRODUCT_SPECIFICATIONS)

        # Регистрация обработчиков редактирования товаров
        dp.message.register(handle_product_editing, ShopStates.EDITING_PRODUCT)
        dp.message.register(process_new_product_name, ShopStates.WAITING_FOR_NEW_PRODUCT_NAME)
        dp.message.register(process_new_product_price, ShopStates.WAITING_FOR_NEW_PRODUCT_PRICE)
        dp.message.register(process_new_product_description, ShopStates.WAITING_FOR_NEW_PRODUCT_DESCRIPTION)
        dp.message.register(process_new_product_specifications, ShopStates.WAITING_FOR_NEW_PRODUCT_SPECS)

        # Регистрация обработчика удаления товаров
        dp.message.register(handle_product_deletion, ShopStates.WAITING_FOR_PRODUCT_ID_TO_DELETE)

        logger.info("All admin handlers registered successfully")

    except Exception as e:
        logger.error(f"Error registering admin handlers: {str(e)}")
        raise

async def handle_product_editing(message: Message, state: FSMContext):
    """Обработчик редактирования товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Starting product editing for user {user_id}, message: {message.text}")

        if message.text == "🔙 Назад к управлению товарами":
            logger.info(f"User {user_id} returning to product management")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "Выберите действие:",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Проверяем, содержит ли сообщение ID товара
        if message.text.startswith(("📝", "💰", "📋", "⚙️", "✅")):
            # Это команда редактирования, передаем её в handle_edit_field
            await handle_edit_field(message, state)
            return

        if "ID:" not in message.text:
            logger.warning(f"Invalid product selection format from user {user_id}: {message.text}")
            await message.answer(
                "⚠️ Пожалуйста, выберите товар из списка",
                reply_markup=create_product_management_keyboard()
            )
            return

        try:
            # Извлекаем ID товара (формат "ID:X - Название")
            product_id = int(message.text.split("ID:")[1].split("-")[0].strip())
            logger.info(f"Extracted product ID: {product_id} for editing")

            # Получаем товар из базы данных
            db = get_db()
            product = db.query(Product).filter(Product.id == product_id).first()
            logger.info(f"Retrieved product from database: {product.name if product else 'Not found'}")

            if not product:
                logger.warning(f"Product with ID {product_id} not found in database")
                await message.answer(
                    "❌ Товар не найден",
                    reply_markup=create_product_management_keyboard()
                )
                return

            # Сохраняем ID товара в состоянии
            await state.update_data(editing_product_id=product_id)
            logger.info(f"Saved product ID {product_id} in state for user {user_id}")

            # Создаем клавиатуру для редактирования
            edit_keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text="📝 Изменить название"),
                        KeyboardButton(text="💰 Изменить цену")
                    ],
                    [
                        KeyboardButton(text="📋 Изменить описание"),
                        KeyboardButton(text="⚙️ Изменить характеристики")
                    ],
                    [
                        KeyboardButton(text="✅ Изменить доступность"),
                        KeyboardButton(text="🔙 Назад к списку товаров")
                    ]
                ],
                resize_keyboard=True,
                persistent=True
            )

            # Показываем информацию о товаре и опции редактирования
            product_info = (
                f"📦 Текущие данные товара:\n\n"
                f"Название: {product.name}\n"
                f"Цена: {product.price:,.2f} руб.\n"
                f"Описание: {product.description}\n"
                f"Характеристики: {product.specifications}\n"
                f"Доступность: {'✅ Доступен' if product.available else '❌ Недоступен'}\n\n"
                f"Выберите, что хотите изменить:"
            )

            await message.answer(product_info, reply_markup=edit_keyboard)
            logger.info(f"Sent product editing menu for product {product_id} to user {user_id}")

        except (ValueError, IndexError) as e:
            logger.error(f"Error extracting product ID: {str(e)}, message: {message.text}")
            await message.answer(
                "❌ Ошибка при определении ID товара",
                reply_markup=create_product_management_keyboard()
            )
            return

    except Exception as e:
        logger.error(f"Error in handle_product_editing: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при редактировании товара",
            reply_markup=create_product_management_keyboard()
        )

async def handle_edit_field(message: Message, state: FSMContext):
    """Обработчик редактирования полей товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Starting edit field handler for user {user_id}, message: {message.text}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        if not product_id:
            logger.error(f"No product_id found in state for user {user_id}")
            await message.answer(
                "❌ Ошибка: товар не выбран",
                reply_markup=create_product_management_keyboard()
            )
            return

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()
        logger.info(f"Retrieved product from database: {product.name if product else 'Not found'}")

        if not product:
            logger.error(f"Product with ID {product_id} not found in database")
            await message.answer(
                "❌ Товар не найден",
                reply_markup=create_product_management_keyboard()
            )
            return

        if message.text == "🔙 Назад к списку товаров":
            logger.info(f"User {user_id} returning to product list")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "Выберите действие:",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Определяем, какое поле редактируем и устанавливаем соответствующее состояние
        field_states = {
            "📝 Изменить название": ShopStates.WAITING_FOR_NEW_PRODUCT_NAME,
            "💰 Изменить цену": ShopStates.WAITING_FOR_NEW_PRODUCT_PRICE,
            "📋 Изменить описание": ShopStates.WAITING_FOR_NEW_PRODUCT_DESCRIPTION,
            "⚙️ Изменить характеристики": ShopStates.WAITING_FOR_NEW_PRODUCT_SPECS,
            "✅ Изменить доступность": None  # Обрабатываем сразу
        }

        if message.text == "✅ Изменить доступность":
            logger.info(f"Changing availability for product {product_id}")
            # Меняем доступность на противоположную
            old_status = product.available
            product.available = not product.available
            try:
                db.commit()
                logger.info(f"Successfully changed product {product_id} availability from {old_status} to {product.available}")
                status = "✅ доступен" if product.available else "❌ недоступен"
                await message.answer(
                    f"Статус товара изменен. Теперь товар {status}",
                    reply_markup=create_product_management_keyboard()
                )
                await state.set_state(ShopStates.ADMIN_PRODUCTS)
            except Exception as e:
                logger.error(f"Failed to update product availability: {str(e)}", exc_info=True)
                db.rollback()
                await message.answer(
                    "❌ Произошла ошибка при изменении доступности товара",
                    reply_markup=create_product_management_keyboard()
                )
            return

        next_state = field_states.get(message.text)
        if next_state:
            logger.info(f"Setting state to {next_state} for user {user_id}")
            await state.set_state(next_state)
            field_prompts = {
                ShopStates.WAITING_FOR_NEW_PRODUCT_NAME: "Введите новое название товара:",
                ShopStates.WAITING_FOR_NEW_PRODUCT_PRICE: "Введите новую цену товара (только число):",
                ShopStates.WAITING_FOR_NEW_PRODUCT_DESCRIPTION: "Введите новое описание товара:",
                ShopStates.WAITING_FOR_NEW_PRODUCT_SPECS: "Введите новые характеристики товара:"
            }
            await message.answer(field_prompts[next_state])
        else:
            logger.warning(f"Unknown action selected: {message.text}")
            await message.answer(
                "⚠️ Выберите действие из меню",
                reply_markup=create_product_management_keyboard()
            )

    except Exception as e:
        logger.error(f"Error in handle_edit_field: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при редактировании товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_name(message: Message, state: FSMContext):
    """Обработчик нового названия товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product name for user {user_id}: {message.text}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_name = product.name
        product.name = message.text
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} name from '{old_name}' to '{message.text}'")
            await message.answer(
                f"✅ Название товара успешно изменено на:\n{message.text}",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product name: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении нового названия",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_name: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении названия",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_price(message: Message, state: FSMContext):
    """Обработчик новой цены товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product price for user {user_id}: {message.text}")

        try:
            new_price = float(message.text)
            if new_price <= 0:
                raise ValueError("Цена должна быть положительным числом")
        except ValueError as e:
            logger.warning(f"Invalid price value: {message.text}")
            await message.answer(
                "❌ Пожалуйста, введите корректное число для цены",
                reply_markup=create_product_management_keyboard()
            )
            return

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_price = product.price
        product.price = new_price
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} price from {old_price} to {new_price}")
            await message.answer(
                f"✅ Цена товара успешно изменена на: {new_price:,.2f} руб.",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product price: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении новой цены",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_price: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении цены",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_description(message: Message, state: FSMContext):
    """Обработчик нового описания товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product description for user {user_id}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_description = product.description
        product.description = message.text
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} description")
            await message.answer(
                f"✅ Описание товара успешно изменено на:\n{message.text}",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product description: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении нового описания",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_description: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении описания",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def process_new_product_specifications(message: Message, state: FSMContext):
    """Обработчик новых характеристик товара"""
    try:
        user_id = message.from_user.id
        logger.info(f"Processing new product specifications for user {user_id}")

        user_data = await state.get_data()
        product_id = user_data.get('editing_product_id')
        logger.info(f"Retrieved product_id from state: {product_id}")

        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            logger.error(f"Product with ID {product_id} not found")
            await message.answer("❌ Товар не найден")
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            return

        old_specs = product.specifications
        product.specifications = message.text
        try:
            db.commit()
            logger.info(f"Successfully updated product {product_id} specifications")
            await message.answer(
                f"✅ Характеристики товара успешно изменены на:\n{message.text}",
                reply_markup=create_product_management_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to update product specifications: {str(e)}", exc_info=True)
            db.rollback()
            await message.answer(
                "❌ Произошла ошибка при сохранении новых характеристик",
                reply_markup=create_product_management_keyboard()
            )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in process_new_product_specifications: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при изменении характеристик",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def show_products_for_deletion(message: Message):
    """Показать список товаров для удаления"""
    try:
        db = get_db()
        products = db.query(Product).all()

        if not products:
            await message.answer(
                "❌ В базе данных нет товаров для удаления",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Создаем клавиатуру со списком товаров
        product_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=f"❌ {product.name} (ID: {product.id})")]
                for product in products
            ] + [[KeyboardButton(text="🔙 Назад к управлению товарами")]],
            resize_keyboard=True,
            persistent=True
        )

        await message.answer(
            "⚠️ Выберите товар для удаления:\n"
            "(это действие нельзя будет отменить)",
            reply_markup=product_keyboard
        )

    except Exception as e:
        logger.error(f"Error in show_products_for_deletion: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при получении списка товаров",
            reply_markup=create_product_management_keyboard()
        )

async def handle_product_deletion(message: Message, state: FSMContext):
    """Обработчик удаления товара"""
    try:
        if message.text == "🔙 Назад к управлению товарами":
            await state.set_state(ShopStates.ADMIN_PRODUCTS)
            await message.answer(
                "Выберите действие:",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Извлекаем ID товара из текста кнопки
        if not message.text.startswith("❌ "):
            await message.answer(
                "⚠️ Пожалуйста, выберите товар из списка",
                reply_markup=create_product_management_keyboard()
            )
            return

        try:
            product_id = int(message.text.split("ID: ")[-1].rstrip(")"))
        except (ValueError, IndexError):
            await message.answer(
                "❌ Ошибка при определении ID товара",
                reply_markup=create_product_management_keyboard()
            )
            return

        # Получаем и удаляем товар из базы данных
        db = get_db()
        product = db.query(Product).filter(Product.id == product_id).first()

        if not product:
            await message.answer(
                "❌ Товар не найден",
                reply_markup=create_product_management_keyboard()
            )
            return

        product_name = product.name
        db.delete(product)
        db.commit()

        await message.answer(
            f"✅ Товар '{product_name}' успешно удален",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

    except Exception as e:
        logger.error(f"Error in handle_product_deletion: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при удалении товара",
            reply_markup=create_product_management_keyboard()
        )
        await state.set_state(ShopStates.ADMIN_PRODUCTS)

async def register_admin_handlers(dp: Dispatcher):
    """Регистрация обработчиков админ-панели"""
    try:
        logger.info("Starting admin handlers registration")

        # Регистрация команды /admin и авторизации
        dp.message.register(admin_start, Command("admin"))
        dp.message.register(check_auth_code, ShopStates.WAITING_FOR_ADMIN_AUTH_CODE)

        # Регистрация обработчиков меню
        dp.message.register(handle_admin_menu, ShopStates.ADMIN_MENU)
        dp.message.register(handle_product_management, ShopStates.ADMIN_PRODUCTS)

        # Регистрация обработчиков добавления товара
        dp.message.register(handle_add_product_name, ShopStates.WAITING_FOR_PRODUCT_NAME)
        dp.message.register(handle_add_product_description, ShopStates.WAITING_FOR_PRODUCT_DESCRIPTION)
        dp.message.register(handle_add_product_price, ShopStates.WAITING_FOR_PRODUCT_PRICE)
        dp.message.register(handle_add_product_category, ShopStates.WAITING_FOR_PRODUCT_CATEGORY)
        dp.message.register(handle_add_product_specifications, ShopStates.WAITING_FOR_PRODUCT_SPECIFICATIONS)

        # Регистрация обработчиков редактирования товаров
        dp.message.register(handle_product_editing, ShopStates.EDITING_PRODUCT)
        dp.message.register(process_new_product_name, ShopStates.WAITING_FOR_NEW_PRODUCT_NAME)
        dp.message.register(process_new_product_price, ShopStates.WAITING_FOR_NEW_PRODUCT_PRICE)
        dp.message.register(process_new_product_description, ShopStates.WAITING_FOR_NEW_PRODUCT_DESCRIPTION)
        dp.message.register(process_new_product_specifications, ShopStates.WAITING_FOR_NEW_PRODUCT_SPECS)

        # Регистрация обработчика удаления товаров
        dp.message.register(handle_product_deletion, ShopStates.WAITING_FOR_PRODUCT_ID_TO_DELETE)

        logger.info("All admin handlers registered successfully")

    except Exception as e:
        logger.error(f"Error registering admin handlers: {str(e)}")
        raise