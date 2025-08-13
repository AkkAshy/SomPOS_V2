import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta


BASE_URL = "https://notify.eskiz.uz/api"
ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL", "asirepovakkanat@gmail.com")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD", "t3sblMZoZDnC5L5Yqx2eZvIeRA6a6FvoP20Gah0F")

# Храним токен и время его жизни в памяти
_eskiz_token = None
_eskiz_token_expire = None


def get_eskiz_token():
    global _eskiz_token, _eskiz_token_expire

    # Если токен есть и он ещё живой
    if _eskiz_token and _eskiz_token_expire and datetime.utcnow() < _eskiz_token_expire:
        return _eskiz_token

    # Если токен есть, но он просрочен → обновляем
    if _eskiz_token and _eskiz_token_expire and datetime.utcnow() >= _eskiz_token_expire:
        try:
            resp = requests.patch(f"{BASE_URL}/auth/refresh", headers={
                "Authorization": f"Bearer {_eskiz_token}"
            })
            if resp.status_code == 200:
                data = resp.json()
                _eskiz_token = data["data"]["token"]
                _eskiz_token_expire = datetime.utcnow() + timedelta(hours=23)
                return _eskiz_token
            else:
                print("❌ Ошибка refresh, перезапрашиваем login...")
        except Exception as e:
            print(f"Ошибка при refresh: {e}")

    # Если токена нет или refresh не сработал — делаем login
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        data={"email": ESKIZ_EMAIL, "password": ESKIZ_PASSWORD}
    )
    login_resp.raise_for_status()
    data = login_resp.json()
    _eskiz_token = data["data"]["token"]
    _eskiz_token_expire = datetime.utcnow() + timedelta(hours=23)  # токен живёт 24ч
    return _eskiz_token

print(get_eskiz_token())