from django.db import transaction
from rest_framework import serializers

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

    @transaction.atomic
    def create(self, validated_data):
        detalles = validated_data.pop("detalles")
        compra = Compra.objects.create(**validated_data)

        for item in detalles:
            producto = item["producto"]
            cantidad = item["cantidad"]
            costo_unitario = item["costo_unitario"]
            DetalleCompra.objects.create(
                compra=compra,
                producto=producto,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
            )
            producto.stock_actual += cantidad
            producto.costo = costo_unitario
            producto.save(update_fields=["stock_actual", "costo"])

        compra.calcular_total()
        return compra


class CompraReadSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)

    class Meta:
        model = Compra
        fields = ["id", "proveedor", "proveedor_nombre", "fecha", "total", "estado"]
