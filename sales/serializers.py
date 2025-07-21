from rest_framework import serializers
from .models import Transaction, TransactionItem
from inventory.models import Product
from customers.models import Customer
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger('sales')

class TransactionItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product'
    )

    class Meta:
        model = TransactionItem
        fields = ['product_id', 'quantity', 'price']

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
        fields = ['id', 'cashier', 'total_amount', 'payment_method', 'status', 
                 'customer_id', 'new_customer', 'items', 'created_at']
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
            if product.stock.quantity < quantity:
                raise serializers.ValidationError(
                    {"items": _(f"Недостаточно товара {product.name} на складе")}
                )
            total_amount += product.sale_price * quantity

        data['total_amount'] = total_amount
        return data

    def create(self, validated_data):
        """
        Creates a new Transaction and its related TransactionItems.

        Takes a validated dictionary with the following keys:
            - items: a list of dictionaries with keys "product" and "quantity"
            - customer_id: an int representing the Customer ID
            - new_customer: a dictionary with keys "full_name" and "phone"
            - cashier: a User object representing the cashier
            - total_amount: a float representing the total amount
            - payment_method: a string representing the payment method
            - status: a string representing the status

        Creates a new Transaction with the given parameters and its related
        TransactionItems. If new_customer is given, it creates a new Customer
        object and assigns it to the transaction. If customer_id is given, it
        assigns the given Customer object to the transaction. Otherwise, it sets
        the customer to None.

        For each item in the items list, it creates a new TransactionItem with
        the given product and quantity, and reduces the quantity of the product
        in the stock.

        Returns the created Transaction object.
        """
        items_data = validated_data.pop('items')
        customer_id = validated_data.pop('customer_id', None)
        new_customer = validated_data.pop('new_customer', None)
        user = self.context['request'].user

        if new_customer:
            customer = Customer.objects.create(
                full_name=new_customer['full_name'],
                phone=new_customer['phone']
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
            TransactionItem.objects.create(
                transaction=transaction,
                product=product,
                quantity=quantity,
                price=product.sale_price
            )
            product.stock.sell(quantity)
            logger.info(
                f"Transaction item created by {user.username}. Transaction ID: {transaction.id}, "
                f"Product ID: {product.id}, Quantity: {quantity}"
            )

        logger.info(
            f"Transaction created by {user.username}. ID: {transaction.id}, Total: {transaction.total_amount}"
        )
        return transaction
    

