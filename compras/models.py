from django.core.validators import MinValueValidator
from django.db import models

from core.models import ModeloBase
from productos.models import Producto


class Proveedor(ModeloBase):
    nombre = models.CharField(max_length=150)
    ruc = models.CharField(max_length=11, unique=True)
    contacto = models.CharField(max_length=150, blank=True)

    class Meta(ModeloBase.Meta):
        ordering = ["nombre"]
        indexes = [models.Index(fields=["ruc"])]

    def __str__(self):
        return f"{self.nombre} ({self.ruc})"


class Compra(ModeloBase):
    ESTADO_CHOICES = [
        ("REGISTRADA", "Registrada"),
        ("ANULADA", "Anulada"),
    ]

    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="compras")
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="REGISTRADA")

    class Meta(ModeloBase.Meta):
        ordering = ["-fecha"]

    def __str__(self):
        return f"Compra #{self.id} - S/. {self.total}"

    def calcular_total(self):
        total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.total = total
        self.save(update_fields=["total"])


class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="detalles_compra")
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.costo_unitario
        super().save(*args, **kwargs)
