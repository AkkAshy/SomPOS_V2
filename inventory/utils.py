# utils/unit_converter.py
CONVERSION_RATES = {
    # длина
    ("m", "cm"): 100,
    ("cm", "m"): 0.01,
    ("m", "mm"): 1000,
    ("mm", "m"): 0.001,
    ("cm", "mm"): 10,
    ("mm", "cm"): 0.1,
    ("inch", "cm"): 2.54,
    ("cm", "inch"): 1 / 2.54,

    # вес
    ("kg", "g"): 1000,
    ("g", "kg"): 0.001,

    # объём
    ("l", "ml"): 1000,
    ("ml", "l"): 0.001,

    # штуки и упаковки можно будет задать отдельно
}

def convert_price(price_per_base_unit, base_unit, sell_unit, quantity):
    """
    price_per_base_unit — цена за базовую единицу (например, за 1 м)
    base_unit — единица хранения товара (например, "m")
    sell_unit — единица продажи (например, "cm")
    quantity — сколько продаём в sell_unit
    """
    if base_unit == sell_unit:
        return price_per_base_unit * quantity

    rate = CONVERSION_RATES.get((sell_unit, base_unit))
    if rate:  
        # Если указали (продаём в cm, а база m) → переводим cm → m
        quantity_in_base = quantity * rate
        return price_per_base_unit * quantity_in_base

    rate = CONVERSION_RATES.get((base_unit, sell_unit))
    if rate:
        # Если указали наоборот (база m, продаём в cm) → переводим cm в m
        quantity_in_base = quantity / rate
        return price_per_base_unit * quantity_in_base

    raise ValueError(f"Нет конверсии из {sell_unit} в {base_unit}")
