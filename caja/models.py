from django.db import models
from django.conf import settings
from django.db.models import Sum, Q

from core.models import ModeloBase


class Caja(ModeloBase):
    ESTADO_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
    ]

    nombre = models.CharField(max_length=100)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    cajero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cajas')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ABIERTA')

    class Meta(ModeloBase.Meta):
        ordering = ['-fecha_apertura']
        verbose_name_plural = 'Cajas'

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"

    @property
    def esta_abierta(self):
        return self.estado == 'ABIERTA'

    @property
    def saldo_actual(self):
        ingresos = self.movimientos.filter(tipo='INGRESO').aggregate(total=Sum('monto'))['total'] or 0
        egresos = self.movimientos.filter(tipo='EGRESO').aggregate(total=Sum('monto'))['total'] or 0
        return self.saldo_inicial + ingresos - egresos


class MovimientoCaja(models.Model):
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
    ]

    caja = models.ForeignKey(Caja, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    concepto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo} - S/{self.monto} ({self.concepto[:30]})"
