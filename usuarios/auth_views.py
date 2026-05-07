from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View personalizado para obtener tokens JWT.
    Usa el serializer custom que incluye validación de usuario activo y rol.
    """
    serializer_class = CustomTokenObtainPairSerializer
    
    @extend_schema(
        summary="Obtener tokens JWT",
        description="Login con username y password. Retorna access token, refresh token, rol y user_id.",
        tags=['Autenticación'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    """
    View personalizado para renovar access token.
    """
    
    @extend_schema(
        summary="Renovar access token",
        description="Usar el refresh token para obtener un nuevo access token.",
        tags=['Autenticación'],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
