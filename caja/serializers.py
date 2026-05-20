from rest_framework import serializers

from caja.models import Caja, MovimientoCaja


class CajaSerializer(serializers.ModelSerializer):
    saldo_actual = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Caja
        fields = [
            "id",
            "nombre",
            "saldo_inicial",
            "saldo_actual",
            "saldo_final",
            "estado",
            "cajero",
            "fecha_apertura",
            "fecha_cierre",
        ]
        read_only_fields = ["saldo_actual", "saldo_final", "estado", "fecha_apertura", "fecha_cierre"]


class MovimientoCajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoCaja
        fields = ["id", "tipo", "monto", "concepto", "fecha", "usuario", "caja"]
        read_only_fields = ["fecha", "usuario"]
