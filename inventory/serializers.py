# inventory/serializers.py
from rest_framework import serializers
from .models import Product, ProductCategory, Stock, ProductBatch
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from drf_yasg.utils import swagger_serializer_method


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['created_at']
        extra_kwargs = {'name': {'trim_whitespace': True}}
        ref_name = 'ProductCategorySerializerInventory'

    def validate_name(self, value):
        value = value.strip()
        if ProductCategory.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                _("Категория с названием '%(name)s' уже существует") % {'name': value},
                code='duplicate_category'
            )
        return value


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=ProductCategory.objects.all(),
        error_messages={
            'does_not_exist': _('Указанная категория не существует'),
            'incorrect_type': _('Некорректный тип данных для категории')
        }
    )
    
    current_stock = serializers.IntegerField(
        source='stock.quantity',
        read_only=True,
        help_text=_('Текущий остаток на складе')
    )

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField)
    def get_current_stock(self, obj):
        return obj.stock.quantity if hasattr(obj, 'stock') else 0
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category',
            'unit', 'sale_price', 'created_at', 'current_stock'
        ]
        read_only_fields = ['created_at', 'current_stock']
        extra_kwargs = {
            'name': {'trim_whitespace': True},
            'barcode': {
                'required': False,
                'allow_null': True,
                'allow_blank': True
            }
        }
        swagger_schema_fields = {
            'example': {
                'name': 'Кока-Кола 0.5л',
                'barcode': '5449000000996',
                'category': 1,
                'unit': 'piece',
                'sale_price': 89.90
            }
        }

    def validate_sale_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                _("Цена не может быть отрицательной"),
                code='negative_price'
            )
        return round(value, 2)

    def validate_barcode(self, value):
        if not value:
            return value
            
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError(
                _("Штрихкод должен содержать только цифры"),
                code='invalid_barcode_format'
            )
            
        if len(value) > 100:
            raise serializers.ValidationError(
                _("Штрихкод не может быть длиннее 100 символов"),
                code='barcode_too_long'
            )
            
        if Product.objects.filter(barcode=value) \
           .exclude(pk=self.instance.pk if self.instance else None) \
           .exists():
            raise serializers.ValidationError(
                _("Товар с таким штрихкодом уже существует"),
                code='duplicate_barcode'
            )
            
        return value


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    
    product_barcode = serializers.CharField(
        source='product.barcode',
        read_only=True,
        allow_null=True
    )
    

    class Meta:
        model = Stock
        fields = [
            'product', 'product_name', 'product_barcode',
            'quantity', 'updated_at'
        ]
        read_only_fields = ['updated_at', 'product_name', 'product_barcode']
        swagger_schema_fields = {
            'example': {
                'product': 1,
                'quantity': 100
            }
        }
        
    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError(
                _("Количество не может быть отрицательным"),
                code='negative_quantity'
            )
        return value

class ProductBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.get_unit_display', read_only=True)

    class Meta:
        model = ProductBatch
        fields = ['id', 'product', 'product_name', 'product_unit', 'quantity', 'expiration_date', 'created_at', 'purchase_price', 'supplier']
        read_only_fields = ['created_at', 'product_name', 'product_unit']
        extra_kwargs = {
            'expiration_date': {'required': False, 'allow_null': True},
            'purchase_price': {'required': False, 'allow_null': True},
            'supplier': {'trim_whitespace': True, 'required': False, 'allow_blank': True},
            'quantity': {'default': 1}
        }
        ref_name = 'ProductBatchSerializerInventory'

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                _("Количество должно быть больше нуля"),
                code='invalid_quantity'
            )
        return value

    def validate(self, data):
        expiration_date = data.get('expiration_date')
        if expiration_date and expiration_date < timezone.now().date():
            raise serializers.ValidationError(
                {'expiration_date': _("Срок годности не может быть в прошлом")},
                code='expired_product'
            )
        return data
    
# class ProductBatchSerializer(serializers.ModelSerializer):
#     product_name = serializers.CharField(
#         source='product.name',
#         read_only=True
#     )
    
#     product_unit = serializers.CharField(
#         source='product.get_unit_display',
#         read_only=True
#     )

#     class Meta:
#         model = ProductBatch
#         fields = [
#             'id', 'product', 'product_name', 'product_unit',
#             'quantity', 'expiration_date', 'created_at',
#             'purchase_price', 'supplier'
#         ]
#         read_only_fields = ['created_at']
#         extra_kwargs = {
#             'expiration_date': {'required': False, 'allow_null': True},
#             'purchase_price': {'required': False, 'allow_null': True},
#             'supplier': {'trim_whitespace': True}
#         }
#         swagger_schema_fields = {
#             'example': {
#                 'product': 1,
#                 'quantity': 100,
#                 'expiration_date': '2024-12-31',
#                 'purchase_price': 50.00,
#                 'supplier': 'ООО Напитки'
#             }
#         }


#     def validate_quantity(self, value):
#         if value <= 0:
#             raise serializers.ValidationError(
#                 _("Количество должно быть больше нуля"),
#                 code='invalid_quantity'
#             )
#         return value

#     def validate(self, data):
#         """
#         Проверка, что срок годности не в прошлом
#         """
#         expiration_date = data.get('expiration_date')
#         if expiration_date and expiration_date < timezone.now().date():
#             raise serializers.ValidationError(
#                 {'expiration_date': _("Срок годности не может быть в прошлом")},
#                 code='expired_product'
#             )
#         return data


class SaleSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(
        min_value=1,
        help_text=_('ID товара для продажи')
    )
    
    quantity = serializers.IntegerField(
        min_value=1,
        help_text=_('Количество товара для продажи')
    )

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                _("Товар с ID %(product_id)s не найден"),
                params={'product_id': value},
                code='product_not_found'
            )
        return value

    def validate(self, data):
        product = Product.objects.get(id=data['product_id'])
        if product.stock.quantity < data['quantity']:
            raise serializers.ValidationError(
                {
                    'quantity': _(
                        "Недостаточно товара на складе. Доступно: %(available)s"
                    ) % {'available': product.stock.quantity}
                },
                code='insufficient_stock'
            )
        return data
    
    class Meta:
        swagger_schema_fields = {
            'example': {
                'product_id': 1,
                'quantity': 2
            }
        }