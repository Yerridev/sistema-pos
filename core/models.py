from django.db import models


class ManagerActivos(models.Manager):
    """Manager que retorna solo registros activos."""

    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class ModeloBase(models.Model):
    """Modelo abstracto con campos comunes de auditoría y soft delete.

    Proporciona:
    - ``activo``: flag de soft delete (default=True).
    - ``creado_en``: timestamp de creación (auto_now_add).
    - ``actualizado_en``: timestamp de última modificación (auto_now).
    - ``eliminar()``: soft delete que desactiva el registro.
    - ``ManagerActivos`` como manager por defecto.
    - ``all_objects``: manager que incluye inactivos.
    """

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = ManagerActivos()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ['-creado_en']

    def eliminar(self):
        """Soft delete: desactiva el registro sin borrarlo."""
        self.activo = False
        self.save(update_fields=['activo', 'actualizado_en'])

    def delete(self, *args, **kwargs):
        """Override para aplicar soft delete ante llamadas directas a delete()."""
        self.activo = False
        self.save(update_fields=['activo', 'actualizado_en'])
        return 1
