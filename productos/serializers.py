from rest_framework import serializers
from .models import Categoria, Producto


class CategoriaSerializer(serializers.ModelSerializer):
    """Serializer para Categoría."""
    productos_count = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion', 'activo', 'productos_count', 'creado_en']

    def get_productos_count(self, obj):
        return obj.productos.count()


class ProductoSerializer(serializers.ModelSerializer):
    """Serializer detallado para Producto."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    stock_critico = serializers.BooleanField(read_only=True)
    ganancia_unitaria = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'codigo_barra', 'nombre', 'categoria', 'categoria_nombre',
            'descripcion', 'precio_venta', 'costo', 'ganancia_unitaria',
            'stock_actual', 'stock_minimo', 'stock_critico', 'unidad',
            'activo', 'creado_en', 'actualizado_en'
        ]

    def validate(self, data):
        """Valida que precio_venta sea mayor que costo."""
        if data.get('precio_venta') and data.get('costo'):
            if data['precio_venta'] < data['costo']:
                raise serializers.ValidationError(
                    "El precio de venta debe ser mayor al costo."
                )
        return data


class ProductoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para lista de productos."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    stock_critico = serializers.BooleanField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'codigo_barra', 'nombre', 'categoria_nombre',
            'precio_venta', 'stock_actual', 'stock_minimo', 'stock_critico',
            'unidad', 'activo'
        ]
