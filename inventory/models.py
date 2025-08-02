import logging
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum, F

logger = logging.getLogger('inventory')

class SizeInfo(models.Model):
    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]


    
    size = models.CharField(max_length=50, verbose_name="Размер")

    chest = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        null=True, 
        blank=True,
        verbose_name="Обхват груди"
    )
    waist = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        null=True, 
        blank=True,
        verbose_name="Обхват талии"
    )
    length = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
        null=True, 
        blank=True,
        verbose_name="Длина"
    )

    class Meta:
        verbose_name = "Размерная информация"
        verbose_name_plural = "Размерные информации"
        unique_together = ('size',)

    def __str__(self):
        return f"{self.size}"


class ProductCategory(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория товара"
        verbose_name_plural = "Категории товаров"
        ordering = ['name']

    def __str__(self): 
        return self.name


class AttributeType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Слаг")
    is_filterable = models.BooleanField(default=False, verbose_name="Фильтруемый ли?")

    class Meta:
        verbose_name = "Тип атрибута"
        verbose_name_plural = "Типы атрибутов"
        ordering = ['name']

    def __str__(self):
        return self.name
    

class AttributeValue(models.Model):
    attribute_type = models.ForeignKey(
        AttributeType,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name="Тип атрибута"

    )
    value = models.CharField(max_length=225, verbose_name="Значение")
    slug = models.SlugField(max_length=225, unique=True, verbose_name="Слаг")
    ordering = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        verbose_name = "Значение атрибута"
        verbose_name_plural = "Значения атрибутов"
        ordering = ['ordering', 'value']
        unique_together = ('attribute_type', 'slug')

    def __str__(self):
        return f"{self.attribute_type.name}: {self.value} ({self.slug})"

class Product(models.Model):
    UNIT_CHOICES = [
        ('piece', 'Штука')
    ]
    name = models.CharField(max_length=255, unique=True, verbose_name="Название")


    barcode = models.CharField(
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True,
        db_index=True,
        verbose_name="Штрих-код"
    )
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Категория"
    )
    unit = models.CharField(
        max_length=50, 
        choices=UNIT_CHOICES, 
        default='piece',
        verbose_name="Единица измерения"
    )
    sale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        validators=[MinValueValidator(0)],
        verbose_name="Цена продажи"
    )
    attributes = models.ManyToManyField(
        AttributeValue,
        blank=True,
        related_name='products',
        verbose_name="Атрибуты"
    )
    size = models.ForeignKey(SizeInfo, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        indexes = [
            models.Index(fields=['name', 'barcode']),
        ]

    def __str__(self): 
        return f"{self.name} ({self.get_unit_display()})"


class ProductAttribute(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_attributes',
        verbose_name="Товар"
    )
    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name='product_attributes',
        verbose_name="Значение атрибута"
    )

    class Meta:
        verbose_name = "Атрибут товара"
        verbose_name_plural = "Атрибуты товаров"
        unique_together = ('product', 'attribute_value')

    def __str__(self):
        return f"{self.product.name} - {self.attribute_value.value}"

class SizeChart(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Таблица размеров"
        verbose_name_plural = "Таблицы размеров"
        ordering = ['name']

    def __str__(self):
        return self.name
    


class ProductBatch(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Количество"
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена закупки",
    )
    supplier = models.CharField(max_length=255, blank=True, verbose_name="Поставщик")
    expiration_date = models.DateField(null=True, blank=True, verbose_name="Дата истечения")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Партия товара"
        verbose_name_plural = "Партии товаров"
        ordering = ['expiration_date', 'created_at']  # FIFO по умолчанию

    def sell(self, quantity):
        if quantity > self.quantity:
            raise ValueError(
                f"Недостаточно товара в партии. Доступно: {self.quantity}, запрошено: {quantity}"
            )
        self.quantity = F('quantity') - quantity
        self.save(update_fields=['quantity'])
        self.refresh_from_db()
        
        if self.quantity == 0:
            self.delete()
            logger.info(f"Партия {self.id} удалена (товар {self.product.name})")
        
        return quantity

    def __str__(self):
        return f"{self.product.name} × {self.quantity} (поставщик: {self.supplier})"

class Stock(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='stock',
        verbose_name="Товар"
    )
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Количество"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Остаток на складе"
        verbose_name_plural = "Остатки на складе"

    def update_quantity(self):
        """Обновляет общее количество товара на основе партий"""
        total = self.product.batches.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        self.quantity = total
        self.save(update_fields=['quantity', 'updated_at'])

    def sell(self, quantity):
        """Списывает товар по FIFO с обработкой ошибок"""
        if quantity <= 0:
            raise ValueError("Количество должно быть положительным")
            
        if self.quantity < quantity:
            raise ValueError(
                f"Недостаточно товара '{self.product.name}'. Доступно: {self.quantity}, запрошено: {quantity}"
            )

        remaining = quantity
        batches = self.product.batches.order_by('expiration_date', 'created_at')
        
        for batch in batches:
            if remaining <= 0:
                break
                
            sell_amount = min(remaining, batch.quantity)
            batch.sell(sell_amount)
            remaining -= sell_amount

        self.update_quantity()
        logger.info(f"Продано {quantity} {self.product.get_unit_display()} {self.product.name}")

    def __str__(self):
        return f"{self.product.name}: {self.quantity} {self.product.get_unit_display()}"

@receiver(post_save, sender=Product)
def create_product_stock(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'stock'):
        Stock.objects.create(product=instance)
        logger.info(f"Создан остаток для товара: {instance.name}")

@receiver(post_save, sender=ProductBatch)
def update_stock_on_batch_change(sender, instance, **kwargs):
    instance.product.stock.update_quantity()