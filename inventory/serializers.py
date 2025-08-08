# inventory/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from drf_yasg.utils import swagger_serializer_method
from decimal import Decimal, ROUND_HALF_UP

from .models import (
    Product, ProductCategory, Stock, ProductBatch, AttributeType,
    AttributeValue, ProductAttribute, SizeChart, SizeInfo, Unit
)



class UnitChoiceSerializer(serializers.ModelSerializer):
    get_name_display = serializers.CharField(read_only=True)
    class Meta:
        model = Unit
        fields = ['id', 'name', 'get_name_display']
    


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

class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ['id', 'attribute_type', 'value', 'slug']

class AttributeTypeSerializer(serializers.ModelSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)
    
    class Meta:
        model = AttributeType
        fields = ['id', 'name', 'slug', 'is_filterable', 'values']

class ProductAttributeSerializer(serializers.ModelSerializer):
    attribute = AttributeValueSerializer(read_only=True)
    attribute_id = serializers.PrimaryKeyRelatedField(
        queryset=AttributeValue.objects.all(),
        source='attribute',
        write_only=True,
        help_text=_('ID значения атрибута')
    )

    class Meta:
        model = ProductAttribute
        fields = ['attribute', 'attribute_id']

class SizeChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeChart
        fields = ['id', 'name', 'description', 'created_at']  # Убрано 'values', так как его нет в модели
        read_only_fields = ['created_at']

class SizeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeInfo
        fields = ['id', 'size', 'chest', 'waist', 'length']
        read_only_fields = ['id']
        swagger_schema_fields = {
            'example': {
                'size': 'XXL',
                'chest': 100,
                'waist': 80,
                'length': 70
            }
        }

from rest_framework import serializers
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import ProductBatch, Product


class ProductBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    size = serializers.SerializerMethodField()

    class Meta:
        model = ProductBatch
        fields = [
            'id',
            'product',
            'product_name',
            'quantity',
            'purchase_price',
            'size',
            'supplier',
            'expiration_date',
            'created_at'
        ]
        read_only_fields = ['created_at', 'product_name', 'size']

    def get_size(self, obj):
        if obj.product and obj.product.size:
            return obj.product.size.size
        return None

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


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    size = SizeInfoSerializer(read_only=True)
    current_stock = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        source='stock.quantity',
        read_only=True,
        help_text=_('Текущий остаток на складе')
    )
    size_id = serializers.PrimaryKeyRelatedField(
        source='size',
        queryset=SizeInfo.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    unit = UnitChoiceSerializer(read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        source='unit',
        queryset=Unit.objects.all(),
        write_only=True,
        required=True,
        help_text=_('ID единицы измерения')
    )
    batches = ProductBatchSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'barcode', 
            'category', 
            'category_name', 
            'sale_price',
            'created_at',
            'size',
            'size_id',
            'unit',
            'unit_id',
            'current_stock',
            'batches',
            'image_label',
        ]
        read_only_fields = ['created_at', 'current_stock']
        extra_kwargs = {
            'name': {'trim_whitespace': True},
            'barcode': {
                'required': False,
                'allow_blank': True
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
        if Product.objects.filter(barcode=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError(
                _("Товар с таким штрихкодом уже существует"),
                code='duplicate_barcode'
            )
        return value
    
    def create(self, validated_data):
        size = validated_data.pop('size', None)
        product = super().create(validated_data)
        if size:
            product.size = size
            product.save()
        return product
    
    def update(self, instance, validated_data):
        size = validated_data.pop('size', None)
        product = super().update(instance, validated_data)
        if size is not None:
            product.size = size
            product.save()
        return product

class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True, allow_null=True)
    unit = UnitChoiceSerializer(source='product.unit', read_only=True)

    class Meta:
        model = Stock
        fields = [
            'product', 'product_name', 'product_barcode', 'unit',
            'quantity', 'updated_at'
        ]
        read_only_fields = ['updated_at', 'product_name', 'product_barcode', 'unit']
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
        product_id = self.initial_data.get('product') or (self.instance.product.id if self.instance else None)
        if product_id:
            product = Product.objects.get(id=product_id)
            quantity_str = str(Decimal(value).quantize(Decimal('0.1') ** product.unit.decimal_places))
            if len(quantity_str.split('.')[-1]) > product.unit.decimal_places:
                raise serializers.ValidationError(
                    f"Количество должно иметь не более {product.unit.decimal_places} знаков после запятой."
                )
        return value.quantize(Decimal('0.1') ** product.unit.decimal_places, rounding=ROUND_HALF_UP)


class ProductMultiSizeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    category = serializers.PrimaryKeyRelatedField(queryset=ProductCategory.objects.all())
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    unit_id = serializers.PrimaryKeyRelatedField(
        source='unit',
        queryset=Unit.objects.all(),
        write_only=True,
        required=True,
        help_text=_('ID единицы измерения')
    )
    batch_info = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        help_text="Список партий с размером и количеством"
    )

    def validate_name(self, value):
        return value.strip()

    def validate_sale_price(self, value):
        return round(value, 2)

    def validate_batch_info(self, value):
        seen_sizes = set()
        unit_id = self.initial_data.get('unit_id')
        if not unit_id:
            raise serializers.ValidationError({"unit_id": "Не указана единица измерения."})
        unit = Unit.objects.get(id=unit_id)

        for item in value:
            size_id = item.get('size_id')
            if not size_id:
                raise serializers.ValidationError("Каждая партия должна содержать size_id.")
            if size_id in seen_sizes:
                raise serializers.ValidationError(f"Размер с ID {size_id} указан дважды.")
            seen_sizes.add(size_id)

            quantity = item.get('quantity')
            if quantity is None:
                raise serializers.ValidationError("Каждая партия должна содержать quantity.")
            if quantity <= 0:
                raise serializers.ValidationError("Количество в партии должно быть больше нуля.")
            quantity_str = str(Decimal(quantity).quantize(Decimal('0.1') ** unit.decimal_places))
            if len(quantity_str.split('.')[-1]) > unit.decimal_places:
                raise serializers.ValidationError(
                    f"Количество в партии должно иметь не более {unit.decimal_places} знаков после запятой."
                )
        return value

    def create(self, validated_data):
        batch_info = validated_data.pop('batch_info')
        base_name = validated_data.pop('name')
        unit = validated_data['unit']
        created_products = []

        for info in batch_info:
            size = SizeInfo.objects.get(pk=info['size_id'])
            quantity = Decimal(info['quantity']).quantize(
                Decimal('0.1') ** unit.decimal_places, rounding=ROUND_HALF_UP
            )
            purchase_price = info.get('purchase_price')
            supplier = info.get('supplier')
            expiration_date = info.get('expiration_date')

            barcode = self._generate_unique_barcode()

            product = Product.objects.create(
                name=base_name,
                barcode=barcode,
                size=size,
                unit=unit,
                **validated_data
            )

            ProductBatch.objects.create(
                product=product,
                quantity=quantity,
                purchase_price=purchase_price,
                supplier=supplier,
                expiration_date=expiration_date
            )

            product.generate_label()
            created_products.append(product)

        return created_products

    def _generate_unique_barcode(self):
        import random
        import time
        while True:
            timestamp = str(int(time.time()))[-8:]
            random_part = str(random.randint(1000, 9999))
            barcode = timestamp + random_part
            if not Product.objects.filter(barcode=barcode).exists():
                return barcode