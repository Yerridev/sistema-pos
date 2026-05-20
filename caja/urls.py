from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CajaViewSet

router = DefaultRouter()
router.register(r'cajas', CajaViewSet, basename='caja')

urlpatterns = [
    path('', include(router.urls)),
]
