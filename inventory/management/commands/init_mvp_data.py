# inventory/management/commands/init_mvp_data.py
from django.core.management.base import BaseCommand
from inventory.models import Unit, ProductCategory, SizeInfo
from django.contrib.auth.models import Group, User

class Command(BaseCommand):
    help = 'Инициализация базовых данных для MVP'

    def handle(self, *args, **kwargs):
        # Создаем базовые единицы измерения
        units_data = [
            ('pcs', 0),  # штуки - целые числа
            ('kg', 3),   # килограммы - до 3 знаков
            ('l', 2),    # литры - до 2 знаков
            ('m', 2),    # метры
            ('pack', 0), # упаковки - целые
        ]
        
        for unit_name, decimal_places in units_data:
            unit, created = Unit.objects.get_or_create(
                name=unit_name,
                defaults={'decimal_places': decimal_places}
            )
            if created:
                self.stdout.write(f'Создана единица: {unit.get_name_display()}')

        # Создаем базовые категории
        categories = [
            'Одежда',
            'Обувь', 
            'Аксессуары',
            'Сантехника',
            'Прочее'
        ]
        
        for cat_name in categories:
            category, created = ProductCategory.objects.get_or_create(name=cat_name)
            if created:
                self.stdout.write(f'Создана категория: {cat_name}')

        # Создаем базовые размеры
        sizes_data = [
            ('XS', 80, 60, 60),
            ('S', 85, 65, 65),
            ('M', 90, 70, 70),
            ('L', 95, 75, 75),
            ('XL', 100, 80, 80),
            ('XXL', 105, 85, 85),
        ]
        
        for size_name, chest, waist, length in sizes_data:
            size, created = SizeInfo.objects.get_or_create(
                size=size_name,
                defaults={
                    'chest': chest,
                    'waist': waist, 
                    'length': length
                }
            )
            if created:
                self.stdout.write(f'Создан размер: {size_name}')

        # Создаем базовые группы пользователей
        groups = ['admin', 'manager', 'cashier', 'stockkeeper']
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'Создана группа: {group_name}')

        # Создаем админа если его нет
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@sompos.com',
                password='admin123',
                first_name='Главный',
                last_name='Администратор'
            )
            admin_group = Group.objects.get(name='admin')
            admin.groups.add(admin_group)
            self.stdout.write('Создан администратор (admin/admin123)')

        self.stdout.write(
            self.style.SUCCESS('MVP данные успешно инициализированы!')
        )