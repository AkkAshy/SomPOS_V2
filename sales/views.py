# sales/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Transaction
from .serializers import TransactionSerializer
from django.utils.translation import gettext_lazy as _

class IsCashierOrManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=['admin', 'manager', 'cashier']).exists()

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsCashierOrManagerOrAdmin]

    @swagger_auto_schema(
        operation_description="Получить список продаж или создать новую продажу",
        responses={200: TransactionSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Создать новую продажу. Для оплаты в долг укажите customer_id или new_customer с full_name и phone.",
        request_body=TransactionSerializer,
        responses={201: TransactionSerializer(), 400: "Invalid data"},
        security=[{'Bearer': []}]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()