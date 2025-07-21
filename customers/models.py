from django.db import models
from django.core.validators import MinValueValidator

class Customer(models.Model):
    full_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Полное имя")
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Телефон")
    email = models.EmailField(null=True, blank=True, verbose_name="Электронная почта")
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Всего потрачено")
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name="Долг")
    loyalty_points = models.PositiveIntegerField(default=0, verbose_name="Бонусные баллы")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Покупатель"
        verbose_name_plural = "Покупатели"

    def __str__(self):
        return self.full_name or self.phone or self.email or "Анонимный покупатель"

    def add_debt(self, amount):
        """Добавляет долг покупателю"""
        self.debt += amount
        self.save(update_fields=['debt'])