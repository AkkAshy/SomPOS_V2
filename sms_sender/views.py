import requests
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import SMS_Template
from .serializators import SmsSenderSerializer
from rest_framework.views import APIView
from .models import SMS_Template as SmsTemplate
from customers.models import Customer as UserProfile
from django.conf import settings

import os
from dotenv import load_dotenv


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


class SendSmsFlexibleView(APIView):
    def post(self, request, template_id=None):
        phone = request.data.get("phone")
        text_message = request.data.get("text")

        # Если текста нет — пробуем взять из шаблона
        if not text_message and template_id:
            try:
                template = SmsTemplate.objects.get(id=template_id)
                text_message = template.text
            except SmsTemplate.DoesNotExist:
                return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        if not text_message:
            return Response({"error": "Text message is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Если номер не указан — берём все номера клиентов
        if phone:
            recipients = [phone]
        else:
            recipients = list(UserProfile.objects.values_list("phone", flat=True))
            if not recipients:
                return Response({"error": "No recipients found"}, status=status.HTTP_404_NOT_FOUND)

        token = get_eskiz_token()
        headers = {"Authorization": f"Bearer {token}"}

        results = []
        for number in recipients:
            payload = {
                "mobile_phone": str(number).replace("+", "").strip(),  # убираем "+"
                "message": text_message,
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
                "phone": number,
                "status_code": response.status_code,
                "response": resp_json
            })

        return Response({"status": "ok", "results": results})
