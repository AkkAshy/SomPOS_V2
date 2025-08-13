# import requests

# ESKIZ_EMAIL = "asirepovakkanat@gmail.com"
# ESKIZ_PASSWORD = "uUF_gss6q!wAEy."
# BASE_URL = "https://notify.eskiz.uz/api"


# def get_eskiz_token():
#     """Авторизация и получение Bearer токена"""
#     response = requests.post(
#         f"{BASE_URL}/auth/login",
#         data={"email": ESKIZ_EMAIL, "password": ESKIZ_PASSWORD}
#     )
#     return response.json()

# print(get_eskiz_token())

import requests

# 1. Логинимся в Eskiz
login_url = "https://notify.eskiz.uz/api/auth/login"
auth_data = {
    'email': 'asirepovakkanat@gmail.com',
    'password': 't3sblMZoZDnC5L5Yqx2eZvIeRA6a6FvoP20Gah0F'
}
login_response = requests.post(login_url, data=auth_data)
login_response.raise_for_status()
token = login_response.json()["data"]["token"]

print("TOKEN:", token)

# 2. Отправляем СМС
send_url = "https://notify.eskiz.uz/api/message/sms/send"
payload = {
    'mobile_phone': '998913865828',
    'from': '4546',
    'message': 'Это тест от Eskiz',
    'callback_url': '',
    'unicode': '0'
}
headers = {
    "Authorization": f"Bearer {token}"
}

send_response = requests.post(send_url, data=payload, headers=headers)

print("STATUS:", send_response.status_code)
try:
    print("RESPONSE:", send_response.json())
except Exception:
    print("RESPONSE TEXT:", send_response.text)

send_response.raise_for_status()

print(send_response.json())
