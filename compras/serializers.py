from rest_framework import serializers

from compras.services import CompraService
from productos.models import Producto
from .models import Compra, DetalleCompra, Proveedor


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ["id", "nombre", "ruc", "contacto", "activo"]


class DetalleCompraSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.filter(activo=True))
    cantidad = serializers.IntegerField(min_value=1)
    costo_unitario = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class CompraSerializer(serializers.ModelSerializer):
    detalles = DetalleCompraSerializer(many=True, write_only=True)

    class Meta:
        model = Compra
        fields = ["id", "proveedor", "fecha", "total", "estado", "detalles"]
        read_only_fields = ["fecha", "total", "estado"]

    def create(self, validated_data):
        detalles = validated_data.pop("detalles")
        usuario = self.context.get("request").user if self.context.get("request") else None
        return CompraService.registrar(
            proveedor=validated_data["proveedor"],
            detalles=detalles,
            usuario=usuario,
        )


class CompraReadSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)

    class Meta:
        model = Compra
        fields = ["id", "proveedor", "proveedor_nombre", "fecha", "total", "estado"]
