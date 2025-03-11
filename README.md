# Telegram Shop Bot

## Требования к серверу
- Python 3.11+
- MySQL 8.0+
- Tesseract OCR
- SSL сертификат для домена (для webhook)

## Установка

### 1. Системные зависимости
```bash
# Обновление пакетов
apt-get update

# Установка необходимых системных пакетов
apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    tesseract-ocr \
    mysql-server \
    libmysqlclient-dev \
    poppler-utils

# Установка утилит для работы с изображениями
apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6
```

### 2. Настройка проекта
```bash
# Клонирование проекта
git clone [your-repository-url]
cd telegram-shop-bot

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей Python
pip install -r requirements.txt
```

### 3. Настройка базы данных
```bash
# Создание базы данных и пользователя MySQL
mysql -u root -p
```

```sql
CREATE DATABASE your_database_name;
CREATE USER 'your_mysql_user'@'localhost' IDENTIFIED BY 'your_mysql_password';
GRANT ALL PRIVILEGES ON your_database_name.* TO 'your_mysql_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Настройка webhook
1. Убедитесь, что у вас есть SSL сертификат для вашего домена
2. В файле .env укажите:
   ```
   WEBHOOK_HOST=https://your-domain.com
   WEBHOOK_PATH=/webhook
   ```
3. Настройте nginx для проксирования запросов:
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/privkey.pem;

       location /webhook {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### 5. Настройка переменных окружения
```bash
# Копирование примера конфигурации
cp .env.example .env

# Отредактируйте файл .env и укажите ваши значения
nano .env
```

### 6. Запуск бота
```bash
# Активация виртуального окружения
source venv/bin/activate

# Запуск бота
python main.py
```

### 7. Настройка автозапуска (systemd)
```bash
# Создание сервиса systemd
sudo nano /etc/systemd/system/telegram-shop-bot.service
```

Содержимое файла сервиса:
```ini
[Unit]
Description=Telegram Shop Bot
After=network.target mysql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/telegram-shop-bot
Environment=PATH=/opt/telegram-shop-bot/venv/bin
ExecStart=/opt/telegram-shop-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Активация и запуск сервиса
sudo systemctl enable telegram-shop-bot
sudo systemctl start telegram-shop-bot
```

## Мониторинг и логи

### Просмотр логов
```bash
# Просмотр логов systemd
sudo journalctl -u telegram-shop-bot -f

# Просмотр логов приложения
tail -f /path/to/telegram-shop-bot/logs/bot.log
```

### Проверка статуса
```bash
sudo systemctl status telegram-shop-bot
```

## Обновление бота
```bash
# Остановка сервиса
sudo systemctl stop telegram-shop-bot

# Обновление кода
git pull

# Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Запуск сервиса
sudo systemctl start telegram-shop-bot
```

## Резервное копирование
```bash
# Бэкап базы данных
mysqldump -u your_mysql_user -p your_database_name > backup.sql

# Бэкап конфигурации
cp .env .env.backup
```

## Устранение неполадок

### Проблемы с отправкой email
1. Проверьте настройки SMTP в .env
2. Убедитесь, что порт 465 открыт для исходящих соединений
3. Проверьте логи на наличие ошибок аутентификации

### Проблемы с распознаванием чеков
1. Проверьте установку Tesseract OCR
2. Убедитесь, что есть права на запись во временную директорию
3. Проверьте качество загружаемых изображений

### Проблемы с webhook
1. Проверьте SSL сертификат (Telegram требует HTTPS)
2. Убедитесь, что порт 5000 открыт и доступен
3. Проверьте настройки nginx и права доступа
4. Просмотрите логи на наличие ошибок подключения

## Поддержка
При возникновении проблем обращайтесь к администратору системы или создавайте issue в репозитории проекта.

### Структура проекта
- `src/` - исходный код проекта
  - `shop/` - модуль магазина
  - `review_handler/` - обработка отзывов
  - `notification/` - отправка уведомлений
  - `receipt_processor/` - обработка чеков
- `main.py` - основной файл запуска бота

### Тестирование
```bash
# Тестирование отправки email
python test_email.py