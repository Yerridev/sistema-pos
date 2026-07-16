from decimal import Decimal

from django.db import transaction

from core.exceptions import RecursoNoEncontrado, ReglaNegocioViolada
from productos.models import Producto

from .models import Compra, DetalleCompra, Proveedor


class ProveedorService:
    """Servicio de dominio para operaciones de proveedores."""

    @classmethod
    def crear(cls, nombre, ruc, contacto=""):
        if not nombre.strip():
            raise ReglaNegocioViolada("El nombre del proveedor es obligatorio.")
        if not ruc or len(ruc) != 11:
            raise ReglaNegocioViolada("El RUC debe tener 11 dígitos.")
        if Proveedor.objects.filter(ruc=ruc).exists():
            raise ReglaNegocioViolada("Ya existe un proveedor con ese RUC.")
        return Proveedor.objects.create(
            nombre=nombre.strip(),
            ruc=ruc,
            contacto=contacto,
        )


class CompraService:
    """Servicio de dominio para registrar compras.

    Es la única fuente de verdad para la creación de compras; las views y
    serializers actúan únicamente como adaptadores delegando aquí.
    """

    @classmethod
    @transaction.atomic
    def registrar(cls, proveedor, detalles):
        """Registra una compra, incrementa stock y actualiza costo de productos.

        Args:
            proveedor: instancia de ``Proveedor`` asociada a la compra.
            detalles: lista de diccionarios con ``producto`` (instancia o pk),
                ``cantidad`` (int > 0) y ``costo_unitario`` (Decimal >= 0).

        Raises:
            ReglaNegocioViolada: si no hay detalles, la cantidad no es mayor
                que cero o el costo unitario es negativo.
            RecursoNoEncontrado: si algún producto no existe o no está activo.
        """
        if not detalles:
            raise ReglaNegocioViolada("Debe enviar al menos un detalle.")

        compra = Compra.objects.create(proveedor=proveedor)
        productos_actualizar = []

        for item in detalles:
            producto = item["producto"]
            if isinstance(producto, Producto):
                producto_id = producto.id
            else:
                producto_id = int(producto)

            cantidad = int(item["cantidad"])
            if cantidad <= 0:
                raise ReglaNegocioViolada("La cantidad debe ser mayor que cero.")

            costo_unitario = item.get("costo_unitario")
            if costo_unitario is None:
                raise ReglaNegocioViolada("El costo unitario es obligatorio.")
            costo_unitario = Decimal(str(costo_unitario))
            if costo_unitario < 0:
                raise ReglaNegocioViolada("El costo unitario no puede ser negativo.")

            try:
                producto = Producto.objects.select_for_update().get(pk=producto_id, activo=True)
            except Producto.DoesNotExist as exc:
                raise RecursoNoEncontrado(f"El producto {producto_id} no existe.") from exc

            DetalleCompra.objects.create(
                compra=compra,
                producto=producto,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
            )
            producto.stock_actual += cantidad
            producto.costo = costo_unitario
            productos_actualizar.append(producto)

        Producto.objects.bulk_update(productos_actualizar, ["stock_actual", "costo"])
        compra.calcular_total()
        return compra
