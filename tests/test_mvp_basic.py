# tests/test_mvp_basic.py
from django.test import TestCase
from django.contrib.auth.models import User, Group
from inventory.models import Unit, Product, ProductCategory, Stock
from sales.models import Transaction, TransactionItem
from customers.models import Customer
from decimal import Decimal

import logging
logging.basicConfig(level=logging.DEBUG)


class MVPBasicTests(TestCase):
    def setUp(self):
        # Создаем тестовые данные
        self.unit = Unit.objects.create(name='pcs', decimal_places=0)
        self.category = ProductCategory.objects.create(name='Тест категория')
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.group = Group.objects.create(name='cashier')
        self.user.groups.add(self.group)

    def test_debug_stock_operations(self):
        """Тест с отладочной информацией"""
        from inventory.models import ProductBatch
        import logging
        
        # Включаем отладку
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger()
        
        product = Product.objects.create(
            name='Debug Товар',
            category=self.category,
            unit=self.unit,
            sale_price=Decimal('200.00'),
            created_by=self.user
        )
        
        print(f"1. Начальный остаток: {product.stock.quantity}")
        
        # Создаем партию товара
        batch = ProductBatch.objects.create(
            product=product,
            quantity=Decimal('10'),
            purchase_price=Decimal('150.00'),
            supplier='Тестовый поставщик'
        )
        
        print(f"2. После создания партии: {product.stock.quantity}")
        
        # Обновляем остаток из базы
        product.stock.refresh_from_db()
        print(f"3. После refresh_from_db: {product.stock.quantity}")
        
        # Проверяем партии
        batches = product.batches.all()
        print(f"4. Количество партий: {batches.count()}")
        for b in batches:
            print(f"   Партия {b.id}: {b.quantity}")
        
        # Продажа
        print("5. Начинаем продажу 3 единиц...")
        product.stock.sell(Decimal('3'))
        
        # Проверяем результат
        product.stock.refresh_from_db()
        print(f"6. После продажи: {product.stock.quantity}")
        
        # Проверяем партии после продажи
        batches = product.batches.all()
        print(f"7. Партии после продажи:")
        for b in batches:
            print(f"   Партия {b.id}: {b.quantity}")
        
        self.assertEqual(product.stock.quantity, Decimal('7'))

    def test_product_creation(self):
        """Тест создания товара"""
        product = Product.objects.create(
            name='Тестовый товар',
            category=self.category,
            unit=self.unit,
            sale_price=Decimal('100.00'),
            created_by=self.user
        )
        
        self.assertEqual(product.name, 'Тестовый товар')
        self.assertTrue(hasattr(product, 'stock'))
        self.assertEqual(product.stock.quantity, Decimal('0'))

    def test_barcode_generation(self):
        """Тест генерации штрих-кода"""
        product = Product.objects.create(
            name='Товар без штрихкода',
            category=self.category,
            unit=self.unit,
            sale_price=Decimal('50.00'),
            created_by=self.user
        )
        
        self.assertIsNotNone(product.barcode)
        self.assertTrue(len(product.barcode) >= 12)

    def test_stock_operations(self):
        """Тест операций со складом"""
        product = Product.objects.create(
            name='Товар для склада',
            category=self.category,
            unit=self.unit,
            sale_price=Decimal('200.00'),
            created_by=self.user
        )
        
        # Проверяем начальный остаток
        self.assertEqual(product.stock.quantity, Decimal('0'))
        
        # Обновляем остаток
        product.stock.quantity = Decimal('10')
        product.stock.save()
        
        # Проверяем продажу
        product.stock.sell(Decimal('3'))
        product.stock.refresh_from_db()
        self.assertEqual(product.stock.quantity, Decimal('7'))

    def test_customer_creation(self):
        """Тест создания клиента"""
        customer = Customer.objects.create(
            full_name='Тестовый Клиент',
            phone='+998901234567'
        )
        
        self.assertEqual(str(customer), 'Тестовый Клиент')
        self.assertEqual(customer.debt, Decimal('0'))

    def test_transaction_creation(self):
        """Тест создания транзакции"""
        # Создаем товар с остатком
        product = Product.objects.create(
            name='Товар для продажи',
            category=self.category,
            unit=self.unit,
            sale_price=Decimal('150.00'),
            created_by=self.user
        )
        product.stock.quantity = Decimal('5')
        product.stock.save()
        
        # Создаем клиента
        customer = Customer.objects.create(
            full_name='Покупатель',
            phone='+998901111111'
        )
        
        # Создаем транзакцию
        transaction = Transaction.objects.create(
            cashier=self.user,
            customer=customer,
            total_amount=Decimal('300.00'),
            payment_method='cash'
        )
        
        # Добавляем товар в транзакцию
        TransactionItem.objects.create(
            transaction=transaction,
            product=product,
            quantity=Decimal('2'),
            price=Decimal('300.00')
        )
        
        # Обрабатываем продажу
        transaction.process_sale()
        
        # Проверяем результат
        product.stock.refresh_from_db()
        logging.debug(f"Stock before sale: {product.stock.quantity}")
        self.assertEqual(product.stock.quantity, Decimal('3'))
        print(product.stock.quantity)
        logging.debug(f"Stock before sale: {product.stock.quantity}")
        self.assertEqual(transaction.status, 'completed')
        return product.stock.quantity
    
    

    def test_debt_transaction(self):
        """Тест продажи в долг"""
        product = Product.objects.create(
            name='Товар в долг',
            category=self.category,
            unit=self.unit,
            sale_price=Decimal('100.00'),
            created_by=self.user
        )
        product.stock.quantity = Decimal('10')
        product.stock.save()
        
        customer = Customer.objects.create(
            full_name='Должник',
            phone='+998902222222'
        )
        
        transaction = Transaction.objects.create(
            cashier=self.user,
            customer=customer,
            total_amount=Decimal('100.00'),
            payment_method='debt'
        )
        
        TransactionItem.objects.create(
            transaction=transaction,
            product=product,
            quantity=Decimal('1'),
            price=Decimal('100.00')
        )
        
        transaction.process_sale()
        
        customer.refresh_from_db()
        self.assertEqual(customer.debt, Decimal('100.00'))


