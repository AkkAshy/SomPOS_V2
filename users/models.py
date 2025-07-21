# auth/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Employee(models.Model):
    ROLE_CHOICES = (
        ('admin', _('Админ')),
        ('stockkeeper', _('Складчик')),
        ('manager', _('Менеджер')),
        ('cashier', _('Кассир')),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    phone = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Сотрудник')
        verbose_name_plural = _('Сотрудники')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"