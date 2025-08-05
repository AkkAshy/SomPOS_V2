# sales/views.py
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from django.db.models import Sum, F, FloatField, DecimalField, Value
from rest_framework import pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.db.models.functions import Coalesce
from drf_yasg import openapi
from .models import Transaction, TransactionHistory, TransactionItem
from .serializers import TransactionSerializer, TransactionHistorySerializer, TransactionItemSerializer, CashierAggregateSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
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


class TransactionHistoryListView(viewsets.ReadOnlyModelViewSet):
    pagination_class = pagination.PageNumberPagination
    queryset = TransactionHistory.objects.all()
    serializer_class = TransactionHistorySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        product = self.request.query_params.get('product')
        customer = self.request.query_params.get('customer')
        cashier = self.request.query_params.get('cashier')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        if product:
            queryset = queryset.filter(details__icontains=product)
        if customer:
            queryset = queryset.filter(details__icontains=customer)
        if cashier:
            queryset = queryset.filter(details__icontains=cashier)

        return queryset

from django.db.models import IntegerField, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
class CashierSalesSummaryView(APIView):
    pagination_class = pagination.PageNumberPagination
    def get(self, request):
        queryset = TransactionItem.objects.values(
            'transaction__cashier_id',
            'transaction__cashier__username'
        ).annotate(
            total_quantity=Coalesce(Sum('quantity'), 0, output_field=IntegerField()),
            total_amount=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('quantity') * F('price'),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ),
                0,
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )

        data = [
            {
                'cashier_id': entry['transaction__cashier_id'],
                'cashier_name': entry['transaction__cashier__username'],
                'total_quantity': entry['total_quantity'],
                'total_amount': entry['total_amount']
            }
            for entry in queryset if entry['transaction__cashier_id'] is not None
        ]

        serializer = CashierAggregateSerializer(data, many=True)
        return Response(serializer.data)
    
