# analytics/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalesAnalyticsViewSet, ProductAnalyticsViewSet, CustomerAnalyticsViewSet

router = DefaultRouter()
router.register(r'sales', SalesAnalyticsViewSet, basename='sales-analytics')
router.register(r'products', ProductAnalyticsViewSet, basename='product-analytics')
router.register(r'customers', CustomerAnalyticsViewSet, basename='customer-analytics')

urlpatterns = [
    path('', include(router.urls)),
]