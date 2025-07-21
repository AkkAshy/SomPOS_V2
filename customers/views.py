from .models import Customer
from .serializers import CustomerSerializer
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    @swagger_auto_schema(
        operation_description="Создание нового клиента",
        request_body=CustomerSerializer,
        responses={
            201: CustomerSerializer,
            400: "Невалидные данные"
        }
    )
    def create(self, request):
        return super().create(request)