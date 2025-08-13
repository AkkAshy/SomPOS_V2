import requests
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import SMS_Template
from .serializators import SmsSenderSerializer
from rest_framework.views import APIView
from .models import SMS_Template as SmsTemplate
from customers.models import Customer as UserProfile
from django.conf import settings
from pathlib import Path

import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

class SmsSenderViewSet(viewsets.ModelViewSet):
    queryset = SMS_Template.objects.all()
    serializer_class = SmsSenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD")

BASE_URL = "https://notify.eskiz.uz/api"


def get_eskiz_token():
    """Авторизация и получение Bearer токена"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"email": ESKIZ_EMAIL, "password": ESKIZ_PASSWORD}
    )
    response.raise_for_status()
    return response.json()["data"]["token"]


def replace_template_variables(text, customer):
    """
    Заменяет переменные в тексте шаблона:
    @ - имя покупателя
    $ - сумма долга покупателя
    """
    if not text:
        return text
    
    # Получаем имя покупателя
    customer_name = customer.full_name or "Уважаемый покупатель"
    
    # Получаем долг покупателя
    debt_amount = str(customer.debt)
    
    # Заменяем переменные
    text = text.replace("@", customer_name)
    text = text.replace("$", debt_amount)
    
    return text


class SendSmsFlexibleView(APIView):
    def post(self, request, template_id=None):
        phone = request.data.get("phone")
        text_message = request.data.get("text")

        # Если текста нет — пробуем взять из шаблона
        template = None
        if not text_message and template_id:
            try:
                template = SmsTemplate.objects.get(id=template_id)
                text_message = template.content  # Используем content вместо text
            except SmsTemplate.DoesNotExist:
                return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        if not text_message:
            return Response({"error": "Text message is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Если номер указан — отправляем конкретному клиенту
        if phone:
            try:
                customer = UserProfile.objects.get(phone=phone)
                recipients = [customer]
            except UserProfile.DoesNotExist:
                return Response({"error": f"Customer with phone {phone} not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Если номер не указан — берём всех клиентов с номерами телефонов
            recipients = UserProfile.objects.filter(phone__isnull=False).exclude(phone="")
            if not recipients:
                return Response({"error": "No recipients found"}, status=status.HTTP_404_NOT_FOUND)

        token = get_eskiz_token()
        headers = {"Authorization": f"Bearer {token}"}

        results = []
        for customer in recipients:
            # Подставляем переменные для каждого клиента индивидуально
            personalized_message = replace_template_variables(text_message, customer)
            
            payload = {
                "mobile_phone": str(customer.phone).replace("+", "").strip(),  # убираем "+"
                "message": personalized_message,
                "country_code": "UZ",
                "callback_url": "",
                "unicode": "1"  # чтобы кириллица не ломалась
            }
            
            response = requests.post(f"{BASE_URL}/message/sms/send-global", headers=headers, data=payload)
            try:
                resp_json = response.json()
            except Exception:
                resp_json = {"error": "Invalid JSON from Eskiz", "raw": response.text}

            results.append({
                "phone": customer.phone,
                "customer_name": customer.full_name or "Не указано",
                "personalized_message": personalized_message,
                "status_code": response.status_code,
                "response": resp_json
            })

        return Response({
            "status": "ok", 
            "template_used": template.name if template else "Custom text",
            "total_sent": len(results),
            "results": results
        })


class TemplatePreviewView(APIView):
    """
    Предварительный просмотр шаблона с подставленными переменными
    """
    def get(self, request, template_id):
        try:
            template = SmsTemplate.objects.get(id=template_id)
        except SmsTemplate.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Получаем ID клиента из параметров запроса (опционально)
        customer_id = request.query_params.get('customer_id')
        
        if customer_id:
            try:
                customer = UserProfile.objects.get(id=customer_id)
            except UserProfile.DoesNotExist:
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Используем первого доступного клиента для примера
            customer = UserProfile.objects.first()
            if not customer:
                return Response({"error": "No customers found for preview"}, status=status.HTTP_404_NOT_FOUND)
        
        # Генерируем превью
        original_content = template.content
        preview_content = replace_template_variables(original_content, customer)
        
        return Response({
            "template_id": template.id,
            "template_name": template.name,
            "original_content": original_content,
            "preview_content": preview_content,
            "customer_used": {
                "id": customer.id,
                "name": customer.full_name or "Не указано",
                "phone": customer.phone,
                "debt": str(customer.debt)
            },
            "available_variables": {
                "@": "имя покупателя",
                "$": "сумма долга"
            }
        })