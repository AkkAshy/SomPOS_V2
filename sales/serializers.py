# sales/serializers.py
from rest_framework import serializers
from .models import Transaction, TransactionItem, TransactionHistory
from inventory.models import Product
from customers.models import Customer
from django.utils.translation import gettext_lazy as _
import logging
import json
from django.contrib.auth import get_user_model
from inventory.utils import CONVERSION_RATES

User = get_user_model()
logger = logging.getLogger('sales')


# --- Конвертация единиц ---
def get_conversion_rate(from_unit, to_unit):
    """Возвращает коэффициент конверсии из одной единицы в другую."""
    if from_unit == to_unit:
        return 1
    rate = CONVERSION_RATES.get((from_unit, to_unit))
    if rate:
        return rate
    reverse_rate = CONVERSION_RATES.get((to_unit, from_unit))
    if reverse_rate:
        return 1 / reverse_rate
    return None


class TransactionItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product'
    )
    sell_unit = serializers.CharField(required=False)

    class Meta:
        model = TransactionItem
        fields = ['product_id', 'quantity', 'sell_unit', 'price']


class TransactionSerializer(serializers.ModelSerializer):
    items = TransactionItemSerializer(many=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), required=False, allow_null=True
    )
    new_customer = serializers.DictField(
        child=serializers.CharField(), required=False
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'cashier', 'total_amount', 'payment_method', 'status',
            'customer_id', 'new_customer', 'items', 'created_at'
        ]
        read_only_fields = ['cashier', 'total_amount', 'created_at']

    def validate(self, data):
        items = data.get('items', [])
        customer_id = data.get('customer_id')
        new_customer = data.get('new_customer')
        payment_method = data.get('payment_method', 'cash')

        if payment_method == 'debt' and not (customer_id or new_customer):
            raise serializers.ValidationError(
                {"error": _("Для оплаты в долг требуется customer_id или new_customer")}
            )

        if new_customer:
            if not new_customer.get('full_name') or not new_customer.get('phone'):
                raise serializers.ValidationError(
                    {"new_customer": _("Поля full_name и phone обязательны")}
                )

        total_amount = 0

        for item in items:
            product = item['product']
            quantity = item['quantity']
            sell_unit = item.get('sell_unit', product.unit.name)

            rate = get_conversion_rate(sell_unit, product.unit.name)
            if rate is None:
                raise serializers.ValidationError(
                    {"items": _(f"Нет конверсии из {sell_unit} в {product.unit.name}")}
                )

            quantity_in_base = quantity * rate

            if product.stock.quantity < quantity_in_base:
                raise serializers.ValidationError(
                    {"items": _(f"Недостаточно товара {product.name} на складе")}
                )

            total_amount += product.sale_price * quantity_in_base

        data['total_amount'] = total_amount
        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        customer_id = validated_data.pop('customer_id', None)
        new_customer = validated_data.pop('new_customer', None)
        user = self.context['request'].user

        if new_customer:
            phone = new_customer['phone']
            customer, _ = Customer.objects.get_or_create(
                phone=phone,
                defaults={'full_name': new_customer['full_name']}
            )
        else:
            customer = Customer.objects.get(id=customer_id) if customer_id else None

        transaction = Transaction.objects.create(
            cashier=user,
            customer=customer,
            **validated_data
        )

        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            sell_unit = item_data.get('sell_unit', product.unit.name)

            rate = get_conversion_rate(sell_unit, product.unit.name)
            quantity_in_base = quantity * rate

            TransactionItem.objects.create(
                transaction=transaction,
                product=product,
                quantity=quantity_in_base,
                price=product.sale_price * quantity_in_base
            )

            logger.info(
                f"Transaction item created by {user.username}. "
                f"Transaction ID: {transaction.id}, Product ID: {product.id}, "
                f"Quantity: {quantity_in_base}"
            )

        transaction.process_sale()

        logger.info(
            f"Transaction created by {user.username}. "
            f"ID: {transaction.id}, Total: {transaction.total_amount}"
        )
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
            return {}


class CashierAggregateSerializer(serializers.Serializer):
    cashier_id = serializers.IntegerField()
    cashier_name = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
