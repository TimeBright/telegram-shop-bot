"""States for the shop module using aiogram FSM."""
from aiogram.fsm.state import State, StatesGroup

class ShopStates(StatesGroup):
    """States for the shop module."""
    # Состояния для покупателя
    WAITING_FOR_CUSTOMER_NAME = State()    # Ожидание имени заказчика
    WAITING_FOR_CUSTOMER_PHONE = State()   # Ожидание телефона заказчика
    WAITING_FOR_CUSTOMER_EMAIL = State()   # Ожидание email заказчика
    WAITING_FOR_DELIVERY_ADDRESS = State()  # Ожидание адреса доставки
    WAITING_FOR_PAYMENT = State()          # Показ QR-кода и ожидание оплаты
    WAITING_FOR_RECEIPT = State()          # Ожидание загрузки чека
    WAITING_FOR_PAYMENT_CONFIRMATION = State()  # Ожидание подтверждения оплаты (проверка чека)
    ORDER_PAID = State()                   # Заказ оплачен, подтвержден чеком

    # Состояния для администратора
    WAITING_FOR_ADMIN_AUTH_CODE = State()  # Ожидание кода авторизации
    WAITING_FOR_ADMIN_EMAIL = State()      # Ожидание email администратора
    WAITING_FOR_ADMIN_PASSWORD = State()   # Ожидание пароля администратора
    WAITING_FOR_EMAIL_VERIFICATION = State()  # Ожидание подтверждения email
    ADMIN_MENU = State()                   # Основное меню админ-панели
    ADMIN_PRODUCTS = State()               # Управление товарами
    ADMIN_ORDERS = State()                 # Управление заказами
    ADMIN_QUESTIONS = State()              # Управление вопросами

    # Состояния для добавления товара
    WAITING_FOR_PRODUCT_NAME = State()         # Ожидание названия товара
    WAITING_FOR_PRODUCT_DESCRIPTION = State()  # Ожидание описания товара
    WAITING_FOR_PRODUCT_PRICE = State()        # Ожидание цены товара
    WAITING_FOR_PRODUCT_CATEGORY = State()     # Ожидание категории товара
    WAITING_FOR_PRODUCT_SPECIFICATIONS = State()  # Ожидание характеристик товара
    WAITING_FOR_PHOTOS = State()               # Ожидание фотографий товара
    EDITING_PRODUCT = State()                  # Редактирование товара
    WAITING_FOR_PRODUCT_ID_TO_DELETE = State() # Ожидание ID товара для удаления

    # Состояния для редактирования товара
    WAITING_FOR_NEW_PRODUCT_NAME = State()        # Ожидание нового названия
    WAITING_FOR_NEW_PRODUCT_PRICE = State()       # Ожидание новой цены
    WAITING_FOR_NEW_PRODUCT_DESCRIPTION = State()  # Ожидание нового описания
    WAITING_FOR_NEW_PRODUCT_SPECS = State()       # Ожидание новых характеристик