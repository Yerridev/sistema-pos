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

    def validate_saldo_inicial(self, value):
        if value < 0:
            raise serializers.ValidationError("El saldo inicial no puede ser negativo.")
        return value


class MovimientoCajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoCaja
        fields = ["id", "tipo", "monto", "concepto", "fecha", "usuario", "caja"]
        read_only_fields = ["fecha", "usuario"]

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor que cero.")
        return value
