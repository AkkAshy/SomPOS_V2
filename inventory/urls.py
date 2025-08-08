# inventory/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'inventory'

# Создаем роутер для ViewSets
router = DefaultRouter()
router.register(r'categories', views.ProductCategoryViewSet, basename='productcategory')
router.register(r'units', views.UnitViewSet, basename='unitchoice')
router.register(r'attribute-types', views.AttributeTypeViewSet, basename='attributetype')
router.register(r'attribute-values', views.AttributeValueViewSet, basename='attributevalue')
router.register(r'size-info', views.SizeInfoViewSet, basename='sizeinfo')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'batches', views.ProductBatchViewSet, basename='productbatch')
router.register(r'stock', views.StockViewSet, basename='stock')



urlpatterns = [
    # ViewSets через роутер
    path('', include(router.urls)),
    
    # Дополнительные эндпоинты
    path('stats/', views.InventoryStatsView.as_view(), name='inventory-stats'),
]

"""
Полный список доступных эндпоинтов:

КАТЕГОРИИ:
- GET    categories/                    - Список всех категорий
- POST   categories/                    - Создать категорию
- GET    categories/{id}/               - Получить категорию
- PUT    categories/{id}/               - Обновить категорию
- PATCH  categories/{id}/               - Частично обновить
- DELETE categories/{id}/               - Удалить категорию

ЕДИНИЦЫ ИЗМЕРЕНИЯ:
- GET    units/                         - Список единиц измерения
- POST   units/                         - Создать единицу измерения
- GET    units/{id}/                    - Получить единицу измерения
- PUT    units/{id}/                    - Обновить единицу измерения
- PATCH  units/{id}/                    - Частично обновить
- DELETE units/{id}/                    - Удалить единицу измерения

ТИПЫ АТРИБУТОВ:
- GET    attribute-types/               - Список типов атрибутов
- POST   attribute-types/               - Создать тип атрибута
- GET    attribute-types/{id}/          - Получить тип атрибута
- PUT    attribute-types/{id}/          - Обновить тип атрибута
- PATCH  attribute-types/{id}/          - Частично обновить
- DELETE attribute-types/{id}/          - Удалить тип атрибута
- GET    attribute-types/for_product_creation/ - Атрибуты для создания товара

ЗНАЧЕНИЯ АТРИБУТОВ:
- GET    attribute-values/              - Список значений атрибутов
- POST   attribute-values/              - Создать значение атрибута
- GET    attribute-values/{id}/         - Получить значение атрибута
- PUT    attribute-values/{id}/         - Обновить значение атрибута
- PATCH  attribute-values/{id}/         - Частично обновить
- DELETE attribute-values/{id}/         - Удалить значение атрибута

РАЗМЕРНАЯ ИНФОРМАЦИЯ:
- GET    size-info/                     - Список размерной информации
- POST   size-info/                     - Создать размерную информацию
- GET    size-info/{id}/                - Получить размерную информацию
- PUT    size-info/{id}/                - Обновить размерную информацию
- PATCH  size-info/{id}/                - Частично обновить
- DELETE size-info/{id}/                - Удалить размерную информацию

ТОВАРЫ:
- GET    products/                      - Список товаров
- POST   products/                      - Создать товар/добавить партию
- GET    products/{id}/                 - Получить товар
- PUT    products/{id}/                 - Обновить товар  
- PATCH  products/{id}/                 - Частично обновить товар
- DELETE products/{id}/                 - Удалить товар
- GET    products/scan_barcode/?barcode=123 - Сканировать штрих-код
- POST   products/create_multi_size/    - Создать товары с разными размерами
- GET    products/available_sizes/      - Получить доступные размеры
- GET    products/available_units/      - Получить доступные единицы измерения
- POST   products/{id}/sell/            - Продать товар
- GET    products/low_stock/?min_quantity=10 - Товары с низким остатком

ПАРТИИ ТОВАРОВ:  
- GET    batches/                       - Список партий
- POST   batches/                       - Создать партию
- GET    batches/{id}/                  - Получить партию
- PUT    batches/{id}/                  - Обновить партию
- PATCH  batches/{id}/                  - Частично обновить партию
- DELETE batches/{id}/                  - Удалить партию
- GET    batches/expiring_soon/?days=7  - Партии с истекающим сроком
- GET    batches/by_product/?product_id=123 - Партии конкретного товара

ОСТАТКИ НА СКЛАДЕ:
- GET    stock/                         - Список остатков
- POST   stock/                         - Создать остаток
- GET    stock/{id}/                    - Получить остаток
- PUT    stock/{id}/                    - Обновить остаток
- PATCH  stock/{id}/                    - Частично обновить остаток
- DELETE stock/{id}/                    - Удалить остаток
- GET    stock/summary/                 - Сводка по остаткам
- POST   stock/{id}/adjust/             - Корректировка остатков
- POST   stock/bulk_adjust/             - Массовая корректировка остатков

СТАТИСТИКА:
- GET    stats/                         - Общая статистика склада

ПРИМЕРЫ ЗАПРОСОВ:

1. Создание товара с размером:
POST /api/inventory/products/
{
    "name": "Футболка Nike",
    "category": 1,
    "sale_price": 5000.00,
    "unit_id": 1,
    "size_id": 2,
    "barcode": "1234567890",
    "batch_info": {
        "quantity": 10,
        "purchase_price": 3000.00,
        "supplier": "Nike Store"
    }
}

2. Создание товаров с множественными размерами:
POST /api/inventory/products/create_multi_size/
{
    "name": "Футболка Адидас",
    "category": 1,
    "sale_price": 4500.00,
    "unit_id": 1,
    "batch_info": [
        {
            "size_id": 1,
            "quantity": 5,
            "purchase_price": 2500.00,
            "supplier": "Адидас Official"
        },
        {
            "size_id": 2,
            "quantity": 8,
            "purchase_price": 2500.00,
            "supplier": "Адидас Official"
        }
    ]
}

3. Сканирование штрих-кода:
GET /api/inventory/products/scan_barcode/?barcode=1234567890

4. Продажа товара:
POST /api/inventory/products/1/sell/
{
    "quantity": 2
}

5. Корректировка остатков:
POST /api/inventory/stock/1/adjust/
{
    "quantity": 15,
    "reason": "Инвентаризация"
}

6. Массовая корректировка остатков:
POST /api/inventory/stock/bulk_adjust/
{
    "adjustments": [
        {
            "product_id": 1,
            "quantity": 20,
            "reason": "Поступление"
        },
        {
            "product_id": 2,
            "quantity": 5,
            "reason": "Возврат"
        }
    ]
}

7. Поиск товаров с низким остатком:
GET /api/inventory/products/low_stock/?min_quantity=5

8. Партии с истекающим сроком:
GET /api/inventory/batches/expiring_soon/?days=30

9. Получение статистики:
GET /api/inventory/stats/

10. Фильтрация товаров по категории:
GET /api/inventory/products/?category=1

11. Поиск товаров:
GET /api/inventory/products/?search=Nike

12. Сортировка товаров по цене:
GET /api/inventory/products/?ordering=sale_price

13. Получение партий конкретного товара:
GET /api/inventory/batches/by_product/?product_id=1

ПАРАМЕТРЫ ФИЛЬТРАЦИИ И ПОИСКА:

Товары (products/):
- category - фильтр по категории
- search - поиск по названию, штрих-коду, категории  
- ordering - сортировка (name, sale_price, created_at)

Партии (batches/):
- product - фильтр по товару
- supplier - фильтр по поставщику
- search - поиск по названию товара, поставщику
- ordering - сортировка (created_at, expiration_date, quantity)

Остатки (stock/):
- product__category - фильтр по категории товара
- search - поиск по названию товара, штрих-коду
- ordering - сортировка (quantity, updated_at)

Категории (categories/):
- search - поиск по названию
- ordering - сортировка (name, created_at)

Единицы измерения (units/):
- search - поиск по названию, короткому названию, коду
- ordering - сортировка (name, kind)

Размерная информация (size-info/):
- search - поиск по размеру
- ordering - сортировка (size)
"""