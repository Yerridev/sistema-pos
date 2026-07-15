from decimal import Decimal

from rest_framework import serializers

from ventas.models import DetalleVenta, Venta


class DetalleVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleVenta
        fields = ["producto", "cantidad", "precio_unitario", "descuento_linea", "subtotal"]
        read_only_fields = ["subtotal"]


class VentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venta
        fields = ["id", "fecha", "cajero", "total", "metodo_pago", "estado"]


class VentaCreateSerializer(serializers.Serializer):
    caja_id = serializers.IntegerField(required=False)
    caja = serializers.IntegerField(required=False, write_only=True)
    metodo_pago = serializers.ChoiceField(choices=Venta.METODO_PAGO_CHOICES, default="EFECTIVO")
    descuento = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    detalles = DetalleVentaSerializer(many=True)

    def validate(self, attrs):
        if not attrs.get("caja_id") and not attrs.get("caja"):
            raise serializers.ValidationError({"caja_id": "La caja es obligatoria."})

        if attrs.get("descuento", Decimal("0.00")) < 0:
            raise serializers.ValidationError({"descuento": "El descuento no puede ser negativo."})

        if not attrs.get("detalles"):
            raise serializers.ValidationError({"detalles": "Debe enviar al menos un detalle."})

        for idx, item in enumerate(attrs["detalles"], start=1):
            cantidad = item["cantidad"]
            if cantidad <= 0:
                raise serializers.ValidationError(
                    {"detalles": f"Detalle {idx}: la cantidad debe ser mayor que cero."}
                )

            descuento_linea = item.get("descuento_linea", Decimal("0.00"))
            if descuento_linea is not None and descuento_linea < 0:
                raise serializers.ValidationError(
                    {"detalles": f"Detalle {idx}: el descuento de línea no puede ser negativo."}
                )

        return attrs


class DetalleVentaReadSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetalleVenta
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "cantidad",
            "precio_unitario",
            "descuento_linea",
            "subtotal",
        ]


class VentaDetalleSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaReadSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = [
            "id",
            "cajero",
            "caja",
            "fecha",
            "subtotal",
            "descuento",
            "igv",
            "total",
            "metodo_pago",
            "estado",
            "motivo_anulacion",
            "anulado_por",
            "fecha_anulacion",
            "detalles",
        ]
