from django.db import models
from django.conf import settings
from django.db.models import Sum
from decimal import Decimal, ROUND_HALF_UP
from productos.models import Producto
from caja.models import Caja


MONEY = Decimal('0.01')
IGV_FACTOR = Decimal('1.18')


def money(value):
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


class Venta(models.Model):
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
    ]
    ESTADO_CHOICES = [
        ('COMPLETADA', 'Completada'),
        ('ANULADA', 'Anulada'),
    ]

    cajero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas')
    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name='ventas')
    fecha = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='COMPLETADA')
    motivo_anulacion = models.TextField(blank=True, null=True)
    anulado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas_anuladas')
    fecha_anulacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"Venta #{self.id} - S/{self.total} ({self.get_estado_display()})"

    def calcular_totales(self):
        importe = self.detalles.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        total = max(importe - self.descuento, Decimal('0.00'))
        subtotal = total / IGV_FACTOR

        self.total = money(total)
        self.subtotal = money(subtotal)
        self.igv = money(self.total - self.subtotal)
        self.save(update_fields=['subtotal', 'igv', 'total'])

    def anular(self, motivo, usuario):
        self.estado = 'ANULADA'
        self.motivo_anulacion = motivo
        self.anulado_por = usuario
        from django.utils import timezone
        self.fecha_anulacion = timezone.now()
        self.save()


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_linea = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"

    def save(self, *args, **kwargs):
        self.subtotal = money((self.precio_unitario * self.cantidad) - self.descuento_linea)
        super().save(*args, **kwargs)
