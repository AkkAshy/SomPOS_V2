# inventory/views.py
from rest_framework import status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.db import transaction, models
from django.db.models import Q, Sum, F, Prefetch
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, NumberFilter, CharFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
from django.core.exceptions import ValidationError
from rest_framework import pagination
from decimal import Decimal

from .models import (
    Product, ProductCategory, Stock, ProductBatch, 
    AttributeType, AttributeValue, ProductAttribute,
    SizeChart, SizeInfo, Unit
)
from .serializers import (
    ProductSerializer, ProductCategorySerializer, StockSerializer,
    ProductBatchSerializer, AttributeTypeSerializer, AttributeValueSerializer,
    ProductAttributeSerializer, SizeChartSerializer, SizeInfoSerializer,
    ProductMultiSizeCreateSerializer, UnitChoiceSerializer
)
from .filters import ProductFilter, ProductBatchFilter, StockFilter

logger = logging.getLogger('inventory')


class UnitViewSet(ModelViewSet):
    """
    ViewSet для управления единицами измерения
    """
    queryset = Unit.objects.all()
    serializer_class = UnitChoiceSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'display_name']
    ordering_fields = ['name', 'kind']
    ordering = ['kind', 'name']


class ProductCategoryViewSet(ModelViewSet):
    """
    ViewSet для управления категориями товаров
    """
    pagination_class = pagination.PageNumberPagination
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @swagger_auto_schema(
        operation_description="Получить все категории товаров",
        responses={200: ProductCategorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Создать новую категорию товара",
        request_body=ProductCategorySerializer,
        responses={
            201: ProductCategorySerializer,
            400: 'Ошибка валидации'
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class AttributeTypeViewSet(ModelViewSet):
    """
    ViewSet для управления типами атрибутов (динамические атрибуты)
    """
    queryset = AttributeType.objects.prefetch_related('values').all()
    serializer_class = AttributeTypeSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name']
    ordering = ['name']

    @swagger_auto_schema(
        operation_description="Получить все типы атрибутов с их значениями",
        responses={200: AttributeTypeSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def for_product_creation(self, request):
        """
        Получить все активные атрибуты для создания товара
        """
        attributes = self.get_queryset().filter(values__isnull=False).distinct()
        serializer = self.get_serializer(attributes, many=True)
        return Response({
            'attributes': serializer.data,
            'message': _('Доступные атрибуты для создания товара')
        })


class AttributeValueViewSet(ModelViewSet):
    """
    ViewSet для управления значениями атрибутов
    """
    queryset = AttributeValue.objects.select_related('attribute_type').all()
    serializer_class = AttributeValueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['attribute_type']
    search_fields = ['value']


class SizeInfoViewSet(ModelViewSet):
    """
    ViewSet для управления размерной информацией
    """
    queryset = SizeInfo.objects.all()
    serializer_class = SizeInfoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]  # MERGED: Комбинируем фильтры
    filterset_fields = ['product', 'size']  # MERGED: Из серверного
    search_fields = ['size']
    ordering_fields = ['size']
    ordering = ['size']

    @swagger_auto_schema(
        operation_description="Создать новую размерную информацию",
        request_body=SizeInfoSerializer,
        responses={
            201: SizeInfoSerializer,
            400: 'Ошибка валидации'
        }
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            size = serializer.save()
            logger.info(f"Создана размерная информация: {size.size}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductViewSet(ModelViewSet):
    """
    ViewSet для управления товарами с поддержкой размеров и единиц измерения
    """
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'barcode', 'category__name', 'created_by__username']
    filterset_fields = ['category', 'created_by']  # MERGED: Убрали дублирование
    ordering_fields = ['name', 'sale_price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Product.objects.select_related(
            'category', 'stock', 'size', 'unit', 'created_by'
        ).prefetch_related(
            Prefetch('batches', queryset=ProductBatch.objects.select_related('product')),
            'product_attributes__attribute_value__attribute_type'  # MERGED: Attributes из серверного
        )

    def perform_create(self, serializer):
        """
        Автоматически устанавливаем created_by при создании товара
        """
        serializer.save(created_by=self.request.user)

    def get_serializer_context(self):
        """
        Передаем контекст с request во все сериализаторы
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @swagger_auto_schema(
        operation_description="Создать товар с учетом штрих-кода",
        request_body=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: 'Ошибка валидации'
        }
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Создание товара с логикой:
        1. Если штрих-код существует - добавляем партию
        2. Если нет - создаем новый товар
        3. Обрабатываем size и unit
        """
        barcode = request.data.get('barcode')
        batch_info = request.data.pop('batch_info', {})
        size_id = request.data.pop('size_id', None)  # MERGED: Из серверного
        unit_id = request.data.get('unit_id')  # MERGED: Для Unit FK

        # Проверяем существование товара по штрих-коду
        if barcode:
            try:
                existing_product = Product.objects.get(barcode=barcode)
                # Товар существует - добавляем партию
                if batch_info:
                    # Приводим quantity к Decimal
                    if 'quantity' in batch_info:
                        batch_info['quantity'] = Decimal(str(batch_info['quantity'])).quantize(
                            Decimal('0.1') ** existing_product.unit.decimal_places
                        )
                    batch_data = {
                        'product': existing_product.id,
                        **batch_info
                    }
                    batch_serializer = ProductBatchSerializer(data=batch_data, context={'request': request})
                    if batch_serializer.is_valid():
                        batch_serializer.save()
                        logger.info(f"Добавлена партия для товара {existing_product.name}")
                        return Response({
                            'message': _('Партия добавлена для существующего товара'),
                            'batch': batch_serializer.data
                        }, status=status.HTTP_201_CREATED)
                    return Response(batch_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                return Response({
                    'message': _('Товар уже существует'),
                    'product': ProductSerializer(existing_product, context={'request': request}).data
                }, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                pass

        # Создаем новый товар
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save(created_by=request.user)
            if batch_info:
                # Приводим quantity к Decimal
                if 'quantity' in batch_info:
                    batch_info['quantity'] = Decimal(str(batch_info['quantity'])).quantize(
                        Decimal('0.1') ** product.unit.decimal_places
                    )
                batch_data = {'product': product.id, **batch_info}
                batch_serializer = ProductBatchSerializer(data=batch_data, context={'request': request})
                if batch_serializer.is_valid():
                    batch_serializer.save()
                    logger.info(f"Создана партия для нового товара {product.name}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Создать товары для множественных размеров",
        request_body=ProductMultiSizeCreateSerializer,
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'products': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            ),
            400: 'Ошибка валидации'
        }
    )
    @action(detail=False, methods=['post'])
    def create_multi_size(self, request):
        """
        Создание товаров с множественными размерами.
        Каждый размер создается как отдельный Product с уникальным штрих-кодом.
        """
        if not request.user.is_authenticated:
            return Response({
                'error': _('Необходима аутентификация')
            }, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ProductMultiSizeCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    created_products = serializer.save(created_by=request.user)
                
                products_data = ProductSerializer(created_products, many=True, context={'request': request}).data
                
                logger.info(f"Создано {len(created_products)} товаров с размерами пользователем {request.user.username}")
                
                return Response({
                    'products': products_data,
                    'message': _('Товары успешно созданы для всех размеров'),
                    'count': len(created_products),
                    'action': 'multi_size_products_created'
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Ошибка при создании товаров с размерами: {str(e)}")
                return Response({
                    'error': _('Ошибка при создании товаров'),
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Сканировать штрих-код и получить информацию о товаре",
        manual_parameters=[
            openapi.Parameter(
                'barcode',
                openapi.IN_QUERY,
                description="Штрих-код для сканирования",
                type=openapi.TYPE_STRING,
                required=True
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def scan_barcode(self, request):
        """
        Сканирование штрих-кода - возвращает товар если существует или форму создания
        """
        barcode = request.query_params.get('barcode')
        if not barcode:
            return Response(
                {'error': _('Штрих-код не указан')},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.select_related('category', 'stock', 'unit').get(barcode=barcode)
            serializer = self.get_serializer(product)
            return Response({
                'found': True,
                'product': serializer.data,
                'message': _('Товар найден')
            })
        except Product.DoesNotExist:
            attributes = AttributeType.objects.prefetch_related('values').all()
            categories = ProductCategory.objects.all()
            units = Unit.objects.all()  # MERGED: Добавили units

            return Response({
                'found': False,
                'barcode': barcode,
                'form_data': {
                    'categories': ProductCategorySerializer(categories, many=True).data,
                    'attributes': AttributeTypeSerializer(attributes, many=True).data,
                    'units': UnitChoiceSerializer(units, many=True).data  # MERGED: Добавили units
                },
                'message': _('Товар не найден. Создайте новый товар.')
            })

    @action(detail=True, methods=['post'])
    def sell(self, request, pk=None):
        """
        Продажа товара (списание со склада)
        """
        product = self.get_object()
        try:
            quantity = Decimal(str(request.data.get('quantity', 0))).quantize(
                Decimal('0.1') ** product.unit.decimal_places
            )
        except (ValueError, TypeError):
            return Response(
                {'error': _('Некорректное количество')},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {'error': _('Количество должно быть больше нуля')},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                product.stock.sell(quantity)
            return Response({
                'message': _('Товар успешно продан'),
                'sold_quantity': str(quantity),
                'remaining_stock': str(product.stock.quantity)
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def available_sizes(self, request):
        """
        Получить все доступные размеры для создания товаров
        """
        sizes = SizeInfo.objects.all().order_by('size')
        serializer = SizeInfoSerializer(sizes, many=True)
        
        return Response({
            'sizes': serializer.data,
            'count': sizes.count(),
            'message': _('Доступные размеры для товаров')
        })

    @action(detail=False, methods=['get'])
    def available_units(self, request):
        """
        Получить все доступные единицы измерения
        """
        units = Unit.objects.all().order_by('kind', 'name')
        serializer = UnitChoiceSerializer(units, many=True)
        
        return Response({
            'units': serializer.data,
            'count': units.count(),
            'message': _('Доступные единицы измерения')
        })

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        Получить товары с низким остатком
        """
        min_quantity = int(request.query_params.get('min_quantity', 10))
        products = self.get_queryset().filter(stock__quantity__lte=min_quantity)

        serializer = self.get_serializer(products, many=True)
        return Response({
            'products': serializer.data,
            'count': products.count(),
            'min_quantity': min_quantity
        })

class ProductBatchViewSet(ModelViewSet):
    """
    ViewSet для управления партиями товаров
    """
    serializer_class = ProductBatchSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductBatchFilter
    filterset_fields = ['product', 'supplier']
    search_fields = ['product__name', 'supplier']
    ordering_fields = ['created_at', 'expiration_date', 'quantity']
    ordering = ['expiration_date', 'created_at']

    def get_queryset(self):
        return ProductBatch.objects.select_related('product').all()

    @swagger_auto_schema(
        operation_description="Создать новую партию товара",
        request_body=ProductBatchSerializer,
        responses={201: ProductBatchSerializer}
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            batch = serializer.save()
            logger.info(f"Создана партия: {batch}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Партии с истекающим сроком годности
        """
        from datetime import date, timedelta
        
        days = int(request.query_params.get('days', 7))
        expiry_date = date.today() + timedelta(days=days)
        
        batches = self.get_queryset().filter(
            expiration_date__lte=expiry_date,
            expiration_date__isnull=False,
            quantity__gt=0  # MERGED: Только партии с остатками из локального
        )
        
        serializer = self.get_serializer(batches, many=True)
        return Response({
            'batches': serializer.data,
            'count': batches.count(),
            'expiring_within_days': days
        })

    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """
        Получить все партии конкретного товара
        """
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response(
                {'error': _('Не указан ID товара')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        batches = self.get_queryset().filter(product_id=product_id)
        serializer = self.get_serializer(batches, many=True)
        
        return Response({
            'batches': serializer.data,
            'count': batches.count(),
            'product_id': product_id
        })


class StockViewSet(ModelViewSet):
    """
    ViewSet для управления остатками на складе с поддержкой точности единиц измерения
    """
    serializer_class = StockSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StockFilter
    search_fields = ['product__name', 'product__barcode']
    filterset_fields = ['product__category']
    ordering_fields = ['quantity', 'updated_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        return Stock.objects.select_related(
            'product', 'product__category', 'product__unit'
        ).all()

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Сводка по остаткам на складе
        """
        queryset = self.get_queryset()
        
        total_products = queryset.count()
        total_quantity = queryset.aggregate(
            total=Sum('quantity')
        )['total'] or Decimal('0')
        
        low_stock_count = queryset.filter(quantity__lte=10).count()
        zero_stock_count = queryset.filter(quantity=0).count()
        
        total_value = ProductBatch.objects.aggregate(
            total=Sum(F('quantity') * F('purchase_price'))
        )['total'] or Decimal('0')
        
        return Response({
            'total_products': total_products,
            'total_quantity': str(total_quantity),  # MERGED: str(Decimal) из локального
            'low_stock_products': low_stock_count,
            'out_of_stock_products': zero_stock_count,
            'total_stock_value': float(total_value)  # MERGED: float для фронта из серверного
        })

    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """
        Корректировка остатков с учетом единиц измерения
        """
        stock = self.get_object()
        new_quantity = request.data.get('quantity')
        reason = request.data.get('reason', 'Корректировка')
        
        if new_quantity is None:
            return Response(
                {'error': _('Не указано количество')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_quantity_decimal = Decimal(str(new_quantity)).quantize(
                Decimal('0.1') ** stock.product.unit.decimal_places
            )
            if new_quantity_decimal < 0:
                return Response(
                    {'error': _('Количество не может быть отрицательным')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # MERGED: Проверка на целое для штучных товаров
            if stock.product.unit.decimal_places == 0 and not new_quantity_decimal.is_integer():
                return Response(
                    {'error': _('Для штучных товаров количество должно быть целым')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': _('Некорректное количество')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_quantity = stock.quantity
        stock.quantity = new_quantity_decimal
        stock.save()
        
        logger.info(
            f"Корректировка остатков {stock.product.name}: "
            f"{old_quantity} -> {new_quantity_decimal}. Причина: {reason}"
        )
        
        return Response({
            'message': _('Остатки скорректированы'),
            'old_quantity': str(old_quantity),
            'new_quantity': str(new_quantity_decimal),
            'reason': reason
        })

    @action(detail=False, methods=['post'])
    def bulk_adjust(self, request):
        """
        Массовая корректировка остатков
        """
        adjustments = request.data.get('adjustments', [])
        if not adjustments:
            return Response(
                {'error': _('Не указаны корректировки')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        errors = []
        
        with transaction.atomic():
            for adjustment in adjustments:
                try:
                    product_id = adjustment.get('product_id')
                    new_quantity = adjustment.get('quantity')
                    reason = adjustment.get('reason', 'Массовая корректировка')
                    
                    stock = Stock.objects.select_related('product__unit').get(
                        product_id=product_id
                    )
                    
                    new_quantity_decimal = Decimal(str(new_quantity)).quantize(
                        Decimal('0.1') ** stock.product.unit.decimal_places
                    )
                    if new_quantity_decimal < 0:
                        raise ValueError(_('Количество не может быть отрицательным'))
                    # MERGED: Проверка на целое для штучных товаров
                    if stock.product.unit.decimal_places == 0 and not new_quantity_decimal.is_integer():
                        raise ValueError(_('Для штучных товаров количество должно быть целым'))
                    
                    old_quantity = stock.quantity
                    stock.quantity = new_quantity_decimal
                    stock.save()
                    
                    results.append({
                        'product_id': product_id,
                        'product_name': stock.product.name,
                        'old_quantity': str(old_quantity),
                        'new_quantity': str(new_quantity_decimal),
                        'reason': reason
                    })
                    
                except Exception as e:
                    errors.append({
                        'product_id': adjustment.get('product_id'),
                        'error': str(e)
                    })
        
        return Response({
            'message': _('Массовая корректировка выполнена'),
            'success_count': len(results),
            'error_count': len(errors),
            'results': results,
            'errors': errors
        })


class InventoryStatsView(generics.GenericAPIView):
    """
    Общая статистика по складу с улучшенными метриками
    """
    
    @swagger_auto_schema(
        operation_description="Получить общую статистику по складу",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_products': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_categories': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_sizes': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_attributes': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_stock_quantity': openapi.Schema(type=openapi.TYPE_STRING),
                    'low_stock_alerts': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'out_of_stock': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_batches': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_units': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'units_breakdown': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'categories_breakdown': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'total_stock_value': openapi.Schema(type=openapi.TYPE_NUMBER),
                }
            )
        }
    )
    def get(self, request):
        stats = {
            'total_products': Product.objects.count(),
            'total_categories': ProductCategory.objects.count(),
            'total_sizes': SizeInfo.objects.count(),
            'total_attributes': AttributeType.objects.count(),
            'total_stock_quantity': str(Stock.objects.aggregate(
                total=Sum('quantity')
            )['total'] or Decimal('0')),
            'low_stock_alerts': Stock.objects.filter(quantity__lte=10).count(),
            'out_of_stock': Stock.objects.filter(quantity=0).count(),
            'total_batches': ProductBatch.objects.count(),
            'total_units': Unit.objects.count(),  # MERGED: Из локального
        }
        
        # Статистика по единицам измерения
        unit_stats = Unit.objects.annotate(
            product_count=models.Count('products')
        ).values('name', 'kind', 'product_count')
        stats['units_breakdown'] = list(unit_stats)
        
        # Статистика по категориям
        category_stats = ProductCategory.objects.annotate(
            product_count=models.Count('products')
        ).values('name', 'product_count')
        stats['categories_breakdown'] = list(category_stats)
        
        # Подсчет общей стоимости склада
        total_value = ProductBatch.objects.aggregate(
            total=Sum(F('quantity') * F('purchase_price'))
        )['total'] or Decimal('0')
        stats['total_stock_value'] = float(total_value)  # MERGED: float для фронта
        
        return Response(stats)