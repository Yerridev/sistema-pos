from decimal import Decimal

from rest_framework import serializers

from caja.models import Caja
from productos.models import Producto
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
        request = self.context["request"]
        user = request.user

        caja_pk = attrs.get("caja_id") or attrs.get("caja")
        if not caja_pk:
            raise serializers.ValidationError({"caja_id": "La caja es obligatoria."})

        try:
            caja = Caja.objects.get(pk=caja_pk)
        except Caja.DoesNotExist as exc:
            raise serializers.ValidationError({"caja_id": "La caja no existe."}) from exc

        if caja.estado != "ABIERTA":
            raise serializers.ValidationError(
                {"caja_id": "La caja debe estar ABIERTA para registrar ventas."}
            )

        if caja.cajero_id != user.id and getattr(user, "rol", None) != "admin":
            raise serializers.ValidationError(
                {"caja_id": "No puede vender en una caja de otro cajero."}
            )

        if attrs["descuento"] < 0:
            raise serializers.ValidationError({"descuento": "El descuento no puede ser negativo."})
        if not attrs["detalles"]:
            raise serializers.ValidationError({"detalles": "Debe enviar al menos un detalle."})

        detalles_validados = []
        for idx, item in enumerate(attrs["detalles"], start=1):
            producto = item["producto"]
            cantidad = item["cantidad"]
            descuento_linea = item.get("descuento_linea", Decimal("0.00"))
            precio_unitario = item.get("precio_unitario") or producto.precio_venta

            if cantidad <= 0:
                raise serializers.ValidationError(
                    {"detalles": f"Detalle {idx}: la cantidad debe ser mayor que cero."}
                )
            if descuento_linea < 0:
                raise serializers.ValidationError(
                    {"detalles": f"Detalle {idx}: el descuento de línea no puede ser negativo."}
                )
            if descuento_linea > (precio_unitario * cantidad):
                raise serializers.ValidationError(
                    {
                        "detalles": (
                            f"Detalle {idx}: el descuento de línea no puede superar "
                            "el subtotal de la línea."
                        )
                    }
                )
            if producto.stock_actual < cantidad:
                raise serializers.ValidationError(
                    {
                        "detalles": (
                            f"Detalle {idx}: stock insuficiente para {producto.nombre}. "
                            f"Disponible: {producto.stock_actual}."
                        )
                    }
                )

            detalles_validados.append(
                {
                    "producto": producto,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "descuento_linea": descuento_linea,
                }
            )

        attrs["caja"] = caja
        attrs["detalles"] = detalles_validados
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
