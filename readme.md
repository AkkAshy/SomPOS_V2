# SomPOS - Point of Sale System

🏪 **Современная система управления продажами для розничных магазинов**

SomPOS - это полнофункциональная система управления продажами (POS), разработанная на Django REST Framework. Система предназначена для автоматизации торговых процессов в розничных магазинах, включая управление товарами, продажами, клиентами и аналитикой.

## 🚀 Основные возможности

### 📦 Управление товарами
- ✅ Создание и редактирование товаров с поддержкой размеров
- ✅ Автоматическая генерация штрих-кодов
- ✅ Управление категориями и единицами измерения
- ✅ Система партий товаров (FIFO)
- ✅ Автоматическая генерация этикеток с штрих-кодами
- ✅ Поддержка атрибутов товаров (размер, цвет, бренд)

### 🏪 Система продаж
- ✅ Быстрое создание чеков
- ✅ Поддержка различных способов оплаты (наличные, карта, перевод, в долг)
- ✅ Сканирование штрих-кодов
- ✅ Автоматическое списание товаров со склада
- ✅ Конвертация единиц измерения при продаже

### 👥 Управление клиентами
- ✅ База данных клиентов
- ✅ Система лояльности
- ✅ Управление долгами
- ✅ История покупок
- ✅ SMS-уведомления

### 📊 Аналитика и отчеты
- ✅ Аналитика продаж по дням/периодам
- ✅ Топ товаров и клиентов
- ✅ Отчеты по кассирам
- ✅ Статистика по остаткам
- ✅ Автоматическое обновление аналитики

### 👤 Система пользователей
- ✅ JWT аутентификация
- ✅ Ролевая модель доступа (админ, менеджер, кассир, складчик)
- ✅ Профили сотрудников
- ✅ Логирование действий

## 🛠️ Технологический стек

- **Backend:** Django 5.2, Django REST Framework
- **База данных:** SQLite (разработка) / PostgreSQL (продакшен)
- **Аутентификация:** JWT токены
- **Документация API:** Swagger/OpenAPI
- **Изображения:** Pillow (генерация штрих-кодов и этикеток)
- **SMS:** Eskiz.uz API
- **Фильтрация:** django-filter
- **Логирование:** Python logging

## 📋 Требования

- Python 3.8+
- Django 5.2+
- PostgreSQL (для продакшена)
- Redis (опционально, для кеширования)

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/sompos.git
cd sompos
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=sompos_db
DB_USER=sompos_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
ESKIZ_EMAIL=your-eskiz-email
ESKIZ_PASSWORD=your-eskiz-password
```

### 5. Применение миграций

```bash
python manage.py migrate
```

### 6. Инициализация базовых данных

```bash
python manage.py init_mvp_data
python manage.py setup_groups
```

### 7. Создание суперпользователя

```bash
python manage.py createsuperuser
```

### 8. Запуск сервера

```bash
python manage.py runserver
```

Система будет доступна по адресу: http://127.0.0.1:8000/

## 📚 Документация API

После запуска сервера документация API доступна по адресам:
- **Swagger UI:** http://127.0.0.1:8000/swagger/
- **ReDoc:** http://127.0.0.1:8000/redoc/

## 🔗 Основные эндпоинты

### Аутентификация
```
POST /users/login/          # Вход в систему
POST /users/register/       # Регистрация пользователя
POST /users/token/refresh/  # Обновление токена
GET  /users/profile/        # Профиль пользователя
```

### Товары
```
GET    /inventory/products/              # Список товаров
POST   /inventory/products/              # Создание товара
GET    /inventory/products/{id}/         # Получение товара
PUT    /inventory/products/{id}/         # Обновление товара
DELETE /inventory/products/{id}/         # Удаление товара
GET    /inventory/products/scan_barcode/ # Сканирование штрих-кода
POST   /inventory/products/create_multi_size/ # Создание товаров с размерами
```

### Продажи
```
GET  /sales/transactions/     # Список продаж
POST /sales/transactions/     # Создание продажи
GET  /sales/transactions/{id}/ # Детали продажи
```

### Клиенты
```
GET  /customers/     # Список клиентов
POST /customers/     # Создание клиента
GET  /customers/{id}/ # Профиль клиента
```

### Аналитика
```
GET /analytics/sales/         # Аналитика продаж
GET /analytics/products/      # Аналитика товаров
GET /analytics/customers/     # Аналитика клиентов
GET /inventory/stats/         # Статистика склада
```

## 📱 Примеры использования

### Создание продажи

```json
POST /sales/transactions/
{
  "payment_method": "cash",
  "customer_id": 1,
  "items": [
    {
      "product_id": 1,
      "quantity": 2,
      "sell_unit": "pcs"
    }
  ]
}
```

### Создание товара с размерами

```json
POST /inventory/products/create_multi_size/
{
  "name": "Футболка Nike",
  "category": 1,
  "sale_price": 5000.00,
  "unit_id": 1,
  "batch_info": [
    {
      "size_id": 1,
      "quantity": 5,
      "purchase_price": 3000.00,
      "supplier": "Nike Store"
    },
    {
      "size_id": 2,
      "quantity": 8,
      "purchase_price": 3000.00,
      "supplier": "Nike Store"
    }
  ]
}
```

### Поиск товара по штрих-коду

```bash
GET /inventory/products/scan_barcode/?barcode=1234567890
```

## 🧪 Тестирование

Запуск тестов:

```bash
# Все тесты
python manage.py test

# Конкретный тест
python manage.py test tests.test_mvp_basic

# С подробным выводом
python manage.py test -v 2
```

## 🔧 Настройка для продакшена

### 1. Настройка PostgreSQL

```bash
sudo -u postgres psql
CREATE DATABASE sompos_db;
CREATE USER sompos_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sompos_db TO sompos_user;
```

### 2. Использование продакшн настроек

```bash
export DJANGO_SETTINGS_MODULE=sompos.settings_production
python manage.py migrate
python manage.py collectstatic
```

### 3. Настройка Nginx (пример)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /path/to/sompos/staticfiles/;
    }

    location /media/ {
        alias /path/to/sompos/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📁 Структура проекта

```
sompos/
├── analytics/          # Модуль аналитики
├── customers/          # Управление клиентами
├── inventory/          # Управление товарами и складом
├── sales/             # Система продаж
├── users/             # Пользователи и аутентификация
├── sms_sender/        # SMS уведомления
├── tests/             # Тесты
├── media/             # Загружаемые файлы
├── static/            # Статические файлы
├── logs/              # Логи приложения
├── manage.py          # Django управление
└── requirements.txt   # Зависимости
```

## 🔐 Роли пользователей

| Роль | Права доступа |
|------|---------------|
| **admin** | Полный доступ ко всем функциям |
| **manager** | Продажи, клиенты, просмотр аналитики |
| **cashier** | Создание продаж, работа с клиентами |
| **stockkeeper** | Управление товарами и складом |

## 📊 Мониторинг и логирование

Все операции логируются в файлы:
- `logs/sompos.log` - общие логи
- `logs/sompos_errors.log` - ошибки

Важные операции логируются по модулям:
- `inventory` - операции с товарами
- `sales` - продажи и транзакции
- `analytics` - обновление аналитики

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 📞 Поддержка

- **Email:** support@sompos.com
- **Документация:** [https://sompos-docs.com](https://sompos-docs.com)
- **Issues:** [GitHub Issues](https://github.com/yourusername/sompos/issues)

## 🎯 Roadmap

- [ ] Мобильное приложение
- [ ] Интеграция с онлайн-кассами
- [ ] Система скидок и промокодов
- [ ] Интеграция с платежными системами
- [ ] Многофилиальность
- [ ] Расширенная аналитика (BI)

---

⭐ **Если проект был полезен, поставьте звездочку!**
