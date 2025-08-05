# auth/urls.py
from django.urls import path
from .views import  RegisterView, ProfileUpdateView, UserListView, ProfileView
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

urlpatterns = [
    path('profile-update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]