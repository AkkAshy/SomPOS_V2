# inventory/utils.py - Обновленная система конвертации
from decimal import Decimal

# Коэффициенты конвертации между единицами измерения
CONVERSION_RATES = {
    # Длина
    ("m", "cm"): Decimal('100'),
    ("cm", "m"): Decimal('0.01'),
    ("m", "mm"): Decimal('1000'),
    ("mm", "m"): Decimal('0.001'),
    ("cm", "mm"): Decimal('10'),
    ("mm", "cm"): Decimal('0.1'),
    ("inch", "cm"): Decimal('2.54'),
    ("cm", "inch"): Decimal('0.393701'),

    # Вес
    ("kg", "g"): Decimal('1000'),
    ("g", "kg"): Decimal('0.001'),

    # Объём
    ("l", "ml"): Decimal('1000'),
    ("ml", "l"): Decimal('0.001'),

    # Штуки и упаковки - по умолчанию 1:1, можно настроить для конкретных товаров
    ("pcs", "pack"): Decimal('1'),
    ("pack", "pcs"): Decimal('1'),
}

def get_conversion_rate(from_unit, to_unit):
    """
    Возвращает коэффициент конвертации из одной единицы измерения в другую.
    
    Args:
        from_unit: Единица измерения, из которой конвертируем
        to_unit: Единица измерения, в которую конвертируем
    
    Returns:
        Decimal: Коэффициент конвертации или None, если конвертация невозможна
    
    Example:
        get_conversion_rate('cm', 'm') -> Decimal('0.01')
        get_conversion_rate('kg', 'g') -> Decimal('1000')
    """
    if from_unit == to_unit:
        return Decimal('1')
    
    # Прямая конвертация
    rate = CONVERSION_RATES.get((from_unit, to_unit))
    if rate is not None:
        return rate
    
    # Обратная конвертация
    reverse_rate = CONVERSION_RATES.get((to_unit, from_unit))
    if reverse_rate is not None:
        return Decimal('1') / reverse_rate
    
    return None

def convert_quantity(quantity, from_unit, to_unit):
    """
    Конвертирует количество из одной единицы измерения в другую.
    
    Args:
        quantity: Количество для конвертации (Decimal или число)
        from_unit: Единица измерения исходного количества
        to_unit: Целевая единица измерения
    
    Returns:
        Decimal: Сконвертированное количество
    
    Raises:
        ValueError: Если конвертация невозможна
    """
    if isinstance(quantity, (int, float, str)):
        quantity = Decimal(str(quantity))
    
    rate = get_conversion_rate(from_unit, to_unit)
    if rate is None:
        raise ValueError(f"Невозможно конвертировать из {from_unit} в {to_unit}")
    
    return quantity * rate

def validate_unit_compatibility(unit1, unit2):
    """
    Проверяет, совместимы ли две единицы измерения для конвертации.
    
    Args:
        unit1: Первая единица измерения
        unit2: Вторая единица измерения
        
    Returns:
        bool: True если единицы совместимы, False иначе
    """
    if unit1 == unit2:
        return True
    
    return get_conversion_rate(unit1, unit2) is not None

def get_compatible_units(base_unit):
    """
    Возвращает список единиц измерения, совместимых с базовой единицей.
    
    Args:
        base_unit: Базовая единица измерения
        
    Returns:
        list: Список совместимых единиц
    """
    compatible = [base_unit]  # Сама единица всегда совместима
    
    for (from_unit, to_unit) in CONVERSION_RATES.keys():
        if from_unit == base_unit and to_unit not in compatible:
            compatible.append(to_unit)
        elif to_unit == base_unit and from_unit not in compatible:
            compatible.append(from_unit)
    
    return compatible

# Функция для обратной совместимости (используется в sales/serializers.py)
def convert_price(price_per_base_unit, base_unit, sell_unit, quantity):
    """
    Вычисляет цену за указанное количество с учетом конвертации единиц.
    
    Args:
        price_per_base_unit: Цена за единицу в базовой единице измерения
        base_unit: Базовая единица измерения товара
        sell_unit: Единица измерения при продаже  
        quantity: Количество в единицах продажи
    
    Returns:
        Decimal: Итоговая цена
    """
    if isinstance(price_per_base_unit, (int, float, str)):
        price_per_base_unit = Decimal(str(price_per_base_unit))
    
    # Конвертируем количество из единиц продажи в базовые единицы
    quantity_in_base = convert_quantity(quantity, sell_unit, base_unit)
    
    # Вычисляем итоговую цену
    return price_per_base_unit * quantity_in_base