from .models import Customer
from .serializers import CustomerSerializer
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework import pagination

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    pagination_class = pagination.PageNumberPagination

    @swagger_auto_schema(
        operation_description="Создание нового клиента",
        request_body=CustomerSerializer,
        responses={
            201: CustomerSerializer,
            400: "Невалидные данные"
        }
    )
    def create(self, request):

        number = request.data.get('number')

        if Customer.objects.filter(number=number).exists():
            return Response(
                {"message": "Клиент с таким номером уже существует."},
                status=400
            )
        else:
            return super().create(request)
        # return super().create(request)