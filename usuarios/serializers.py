from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para obtener tokens JWT.
    Incluye validación de usuario activo y rol en el response.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        
        # Validar que el usuario esté activo
        if not user.is_active:
            raise serializers.ValidationError("El usuario no está activo.")
        
        # Agregar rol al response
        data['rol'] = user.rol
        data['user_id'] = user.id
        
        return data
