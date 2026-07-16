from django.core.validators import MinValueValidator
from django.db import models

from core.models import ModeloBase


class Categoria(ModeloBase):
    """Categoría de productos."""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta(ModeloBase.Meta):
        ordering = ['nombre']
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


class Producto(ModeloBase):
    """Producto del inventario."""
    UNIDAD_CHOICES = [
        ('unidad', 'Unidad'),
        ('kg', 'Kilogramo'),
        ('litro', 'Litro'),
        ('metro', 'Metro'),
        ('docena', 'Docena'),
    ]

    codigo_barra = models.CharField(max_length=50, unique=True, blank=True, null=True)
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    descripcion = models.TextField(blank=True, null=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    costo = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock_actual = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    stock_minimo = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    unidad = models.CharField(max_length=20, choices=UNIDAD_CHOICES, default='unidad')

    class Meta(ModeloBase.Meta):
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['codigo_barra']),
            models.Index(fields=['categoria']),
            models.Index(fields=['activo']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(stock_actual__gte=0),
                name='stock_no_negativo',
            ),
            models.CheckConstraint(
                check=models.Q(precio_venta__gte=models.F('costo')),
                name='precio_venta_mayor_igual_costo',
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.stock_actual} {self.unidad})"

    @property
    def stock_critico(self):
        """Retorna True si el stock está por debajo del mínimo."""
        return self.stock_actual < self.stock_minimo

    @property
    def ganancia_unitaria(self):
        """Calcula la ganancia por unidad."""
        return self.precio_venta - self.costo
