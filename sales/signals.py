# sales/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction, TransactionHistory
import json

@receiver(post_save, sender=Transaction)
def log_transaction(sender, instance, created, **kwargs):
    action = 'created' if created else instance.status
    details = {
        'total_amount': str(instance.total_amount),
        'payment_method': instance.payment_method,
        'cashier': instance.cashier.username if instance.cashier else None,
        'customer': instance.customer.full_name if instance.customer else None,
        'items': [
            {'product': item.product.name, 'quantity': item.quantity, 'price': str(item.price)}
            for item in instance.items.all()
        ]
    }
    TransactionHistory.objects.create(
        transaction=instance,
        action=action,
        details=json.dumps(details, ensure_ascii=False)
    )