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
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Unit
        fields = ['id', 'name', 'display_name', 'decimal_places']


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


############################################################# Атрибуты #############################################################
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
############################################################# Атрибуты конец #############################################################


class SizeChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeChart
        fields = ['id', 'name', 'description', 'created_at']
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


############################################################## Продукты #############################################################

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
        """Возвращает размер из поля size модели Product"""
        if obj.product and obj.product.size:
            return obj.product.size.size
        return None

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                _("Количество должно быть больше нуля"),
                code='invalid_quantity'
            )
        
        # Приводим к Decimal и округляем согласно единице измерения продукта
        if hasattr(self, 'instance') and self.instance and self.instance.product:
            unit = self.instance.product.unit
            return Decimal(str(value)).quantize(
                Decimal('0.1') ** unit.decimal_places, rounding=ROUND_HALF_UP
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
        queryset=Unit.objects.all(),  # ← Правильно
        write_only=True,
        required=True,
        help_text=_('ID единицы измерения')
    )
    batches = ProductBatchSerializer(
        many=True,
        read_only=True,
        help_text=_('Партии товара')
    )

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
            'created_by'
        ]
        read_only_fields = ['created_at', 'current_stock', 'created_by']
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

        if Product.objects.filter(barcode=value) \
           .exclude(pk=self.instance.pk if self.instance else None) \
           .exists():
            raise serializers.ValidationError(
                _("Товар с таким штрихкодом уже существует"),
                code='duplicate_barcode'
            )

        return value

    def create(self, validated_data):
        """
        Создание товара с правильной обработкой размера
        """
        validated_data.pop('created_by', None)
        size = validated_data.pop('size', None)

        user = self.context['request'].user

        # Создаем товар БЕЗ размера
        product = Product.objects.create(created_by=user, **validated_data)

        # Устанавливаем размер ПОСЛЕ создания
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
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    product_barcode = serializers.CharField(
        source='product.barcode',
        read_only=True,
        allow_null=True
    )
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
        
        # Добавляем валидацию decimal_places
        product_id = self.initial_data.get('product') or (self.instance.product.id if self.instance else None)
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                quantity_decimal = Decimal(str(value)).quantize(
                    Decimal('0.1') ** product.unit.decimal_places, rounding=ROUND_HALF_UP
                )
                # Проверяем на целочисленность для штучных товаров
                if product.unit.decimal_places == 0 and not quantity_decimal.is_integer():
                    raise serializers.ValidationError(
                        "Для штучных товаров количество должно быть целым."
                    )
                return quantity_decimal
            except Product.DoesNotExist:
                pass
        
        return value


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
    size_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
        required=False,
        help_text="Список ID размеров (для одежды, optional для сантехники)"
    )
    batch_info = serializers.JSONField(required=False)

    def validate_name(self, value):
        return value.strip()

    def validate_sale_price(self, value):
        return round(value, 2)

    def validate(self, data):
        """Проверяем комбинации для совместимости"""
        size_ids = data.get('size_ids')
        batch_info = data.get('batch_info')
        
        if not size_ids and not batch_info:
            # Для сантехники позволяем создать один продукт без дополнительной информации
            return data
        
        if batch_info and isinstance(batch_info, list) and size_ids:
            raise serializers.ValidationError(
                "Если batch_info — list (с size_id в каждом), не используйте size_ids одновременно"
            )
        
        return data

    def validate_batch_info(self, value):
        if not value:
            return value
        
        unit = Unit.objects.get(id=self.initial_data.get('unit_id'))
        
        if isinstance(value, dict):
            # Старый формат: dict без size_id
            quantity = value.get('quantity')
            if quantity is None:
                raise serializers.ValidationError("batch_info (dict) должен содержать quantity.")
            if quantity <= 0:
                raise serializers.ValidationError("Количество должно быть больше нуля.")
            
            quantity_decimal = Decimal(str(quantity)).quantize(
                Decimal('0.1') ** unit.decimal_places, rounding=ROUND_HALF_UP
            )
            value['quantity'] = quantity_decimal
            
            expiration_date = value.get('expiration_date')
            if expiration_date and expiration_date < timezone.now().date():
                raise serializers.ValidationError("Срок годности в прошлом.")
            
            return value
        
        elif isinstance(value, list):
            # Новый формат: list dict, каждый с size_id
            seen_sizes = set()
            for item in value:
                size_id = item.get('size_id')
                if size_id is None:
                    raise serializers.ValidationError("Каждый item в batch_info (list) должен иметь size_id.")
                if size_id in seen_sizes:
                    raise serializers.ValidationError(f"Size_id {size_id} дублируется.")
                seen_sizes.add(size_id)
                
                quantity = item.get('quantity')
                if quantity is None:
                    raise serializers.ValidationError("Каждый item должен иметь quantity.")
                if quantity <= 0:
                    raise serializers.ValidationError("Количество должно быть больше нуля.")
                
                quantity_decimal = Decimal(str(quantity)).quantize(
                    Decimal('0.1') ** unit.decimal_places, rounding=ROUND_HALF_UP
                )
                item['quantity'] = quantity_decimal
                
                expiration_date = item.get('expiration_date')
                if expiration_date and expiration_date < timezone.now().date():
                    raise serializers.ValidationError("Срок годности в прошлом.")
            
            return value
        
        else:
            raise serializers.ValidationError("batch_info должен быть dict или list dict.")

    def save(self, **kwargs):
        created_by = kwargs.get('created_by')
        if not created_by:
            raise serializers.ValidationError("created_by required")

        validated_data = self.validated_data
        size_ids = validated_data.pop('size_ids', [])
        batch_info = validated_data.pop('batch_info', None)
        unit = validated_data['unit']
        base_name = validated_data['name']

        created_products = []

        if isinstance(batch_info, list):
            # Новый формат: каждый item — отдельный продукт с size_id и своей партией
            for info in batch_info:
                size_id = info.pop('size_id')
                try:
                    size_instance = SizeInfo.objects.get(id=size_id)
                except SizeInfo.DoesNotExist:
                    raise serializers.ValidationError(f"Size {size_id} not exist")

                product_name = f"{base_name} - {size_instance.size}" if size_instance else base_name
                barcode = self.generate_unique_barcode()

                product_data = {
                    **validated_data,
                    'name': product_name,
                    'barcode': barcode,
                    'created_by': created_by,
                    'size': size_instance,
                    'unit': unit
                }

                product = Product.objects.create(**product_data)

                # Создаем партию из оставшихся info
                if info:
                    ProductBatch.objects.create(
                        product=product,
                        **info
                    )

                product.generate_label()
                created_products.append(product)

        else:
            # Старый формат или сантехника: size_ids (или пустой для одного), batch_info dict общий
            if not size_ids:
                # Для сантехники: создать один без size
                size_ids = [None]

            for size_id in size_ids:
                size_instance = None
                if size_id:
                    try:
                        size_instance = SizeInfo.objects.get(id=size_id)
                    except SizeInfo.DoesNotExist:
                        raise serializers.ValidationError(f"Size {size_id} not exist")

                product_name = f"{base_name} - {size_instance.size}" if size_instance else base_name
                barcode = self.generate_unique_barcode()

                product_data = {
                    **validated_data,
                    'name': product_name,
                    'barcode': barcode,
                    'created_by': created_by,
                    'size': size_instance,
                    'unit': unit
                }

                product = Product.objects.create(**product_data)

                # Добавляем общую партию, если dict
                if batch_info:
                    ProductBatch.objects.create(
                        product=product,
                        **batch_info
                    )

                product.generate_label()
                created_products.append(product)

        return created_products

    def generate_unique_barcode(self):
        """Генерирует уникальный штрих-код"""
        import uuid
        return str(uuid.uuid4().int)[:12]


############################################################### Продукты конец #############################################################