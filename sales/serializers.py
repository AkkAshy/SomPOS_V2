# sales/serializers.py
from rest_framework import serializers
from .models import Transaction, TransactionItem, TransactionHistory
from inventory.models import Product
from customers.models import Customer
from django.utils.translation import gettext_lazy as _
from decimal import Decimal, ROUND_HALF_UP
import logging
import json
from django.contrib.auth import get_user_model
from inventory.utils import get_conversion_rate, convert_quantity, validate_unit_compatibility

User = get_user_model()
logger = logging.getLogger('sales')


class TransactionItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.select_related('unit', 'stock').all(), 
        source='product'
    )
    sell_unit = serializers.CharField(
        required=False,
        help_text="Единица измерения для продажи"
    )
    
    class Meta:
        model = TransactionItem
        fields = ['product_id', 'quantity', 'sell_unit', 'price']
        read_only_fields = ['price']


class TransactionSerializer(serializers.ModelSerializer):
    items = TransactionItemSerializer(many=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), 
        required=False, 
        allow_null=True,
        source='customer'
    )
    new_customer = serializers.DictField(
        child=serializers.CharField(), 
        required=False,
        help_text="Данные нового клиента: {'full_name': '...', 'phone': '...'}"
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'cashier', 'total_amount', 'payment_method', 'status',
            'customer_id', 'new_customer', 'items', 'created_at'
        ]
        read_only_fields = ['cashier', 'total_amount', 'created_at', 'id', 'status']

    def validate(self, data):
        items = data.get('items', [])
        customer = data.get('customer')  # Изменено с customer_id на customer
        new_customer = data.get('new_customer')
        payment_method = data.get('payment_method', 'cash')

        # Валидация клиента для долговой продажи
        if payment_method == 'debt' and not (customer or new_customer):
            raise serializers.ValidationError({
                "payment_method": _("Для оплаты в долг требуется указать customer_id или new_customer")
            })

        if new_customer:
            required_fields = ['full_name', 'phone']
            missing_fields = [field for field in required_fields if not new_customer.get(field)]
            if missing_fields:
                raise serializers.ValidationError({
                    "new_customer": _(f"Обязательные поля отсутствуют: {', '.join(missing_fields)}")
                })

        # Валидация товаров и расчет общей суммы
        if not items:
            raise serializers.ValidationError({
                "items": _("Список товаров не может быть пустым")
            })

        total_amount = Decimal('0')
        processed_items = []

        for i, item in enumerate(items):
            try:
                product = item['product']
                quantity = item['quantity']
                sell_unit = item.get('sell_unit', product.unit.name)

                # Валидация количества
                if quantity <= 0:
                    raise serializers.ValidationError({
                        f"items[{i}].quantity": _("Количество должно быть больше нуля")
                    })

                # Проверка совместимости единиц измерения
                if not validate_unit_compatibility(sell_unit, product.unit.name):
                    raise serializers.ValidationError({
                        f"items[{i}].sell_unit": _(
                            f"Единица '{sell_unit}' несовместима с базовой единицей товара '{product.unit.name}'"
                        )
                    })

                # Конвертация в базовые единицы
                try:
                    base_quantity = convert_quantity(quantity, sell_unit, product.unit.name)
                except ValueError as e:
                    raise serializers.ValidationError({
                        f"items[{i}].sell_unit": _(f"Ошибка конвертации: {str(e)}")
                    })

                # Проверка остатков на складе
                if not hasattr(product, 'stock'):
                    raise serializers.ValidationError({
                        f"items[{i}].product_id": _(f"У товара '{product.name}' нет информации об остатках")
                    })

                if product.stock.quantity < base_quantity:
                    raise serializers.ValidationError({
                        f"items[{i}]": _(
                            f"Недостаточно товара '{product.name}' на складе. "
                            f"Запрошено: {quantity} {sell_unit} "
                            f"({base_quantity} {product.unit.name}), "
                            f"доступно: {product.stock.quantity} {product.unit.name}"
                        )
                    })

                # Расчет цены
                item_price = product.sale_price * base_quantity
                total_amount += item_price

                # Сохраняем обработанные данные
                processed_items.append({
                    'product': product,
                    'quantity': quantity,
                    'sell_unit': sell_unit,
                    'base_quantity': base_quantity,
                    'item_price': item_price
                })

                logger.debug(
                    f"Item {i}: {product.name}, "
                    f"sell: {quantity} {sell_unit}, "
                    f"base: {base_quantity} {product.unit.name}, "
                    f"price: {item_price}"
                )

            except KeyError as e:
                raise serializers.ValidationError({
                    f"items[{i}]": _(f"Отсутствует обязательное поле: {str(e)}")
                })

        # Сохраняем обработанные данные для использования в create()
        data['_processed_items'] = processed_items
        data['total_amount'] = total_amount

        return data

    def create(self, validated_data):
        processed_items = validated_data.pop('_processed_items', [])
        validated_data.pop('items', [])  # Убираем исходные items
        customer = validated_data.pop('customer', None)
        new_customer_data = validated_data.pop('new_customer', None)
        user = self.context['request'].user

        # Создание или получение клиента
        if new_customer_data:
            phone = new_customer_data['phone']
            customer, created = Customer.objects.get_or_create(
                phone=phone,
                defaults={
                    'full_name': new_customer_data['full_name']
                }
            )
            if created:
                logger.info(f"Создан новый клиент: {customer.full_name} ({customer.phone})")

        # Создание транзакции
        transaction = Transaction.objects.create(
            cashier=user,
            customer=customer,
            **validated_data
        )

        # Создание элементов транзакции
        for item_data in processed_items:
            transaction_item = TransactionItem.objects.create(
                transaction=transaction,
                product=item_data['product'],
                quantity=item_data['base_quantity'],
                price=item_data['item_price']
            )
            
            logger.info(
                f"Создан элемент транзакции: {item_data['product'].name} "
                f"({item_data['quantity']} {item_data['sell_unit']} = "
                f"{item_data['base_quantity']} {item_data['product'].unit.name}), "
                f"цена: {item_data['item_price']}"
            )

        # Обработка продажи (списание со склада, обновление данных клиента)
        try:
            transaction.process_sale()
            logger.info(
                f"Транзакция {transaction.id} успешно обработана. "
                f"Кассир: {user.username}, Сумма: {transaction.total_amount}, "
                f"Способ оплаты: {transaction.payment_method}"
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке транзакции {transaction.id}: {str(e)}")
            # В идеале здесь должна быть откат транзакции
            raise serializers.ValidationError({
                "transaction": _(f"Ошибка при обработке продажи: {str(e)}")
            })

        return transaction


class TransactionHistorySerializer(serializers.ModelSerializer):
    parsed_details = serializers.SerializerMethodField()

    class Meta:
        model = TransactionHistory
        fields = ['id', 'transaction', 'action', 'parsed_details', 'created_at']

    def get_parsed_details(self, obj):
        try:
            return json.loads(obj.details)
        except json.JSONDecodeError:
            return {"raw_details": obj.details}


class CashierAggregateSerializer(serializers.Serializer):
    cashier_id = serializers.IntegerField()
    cashier_name = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)