from decimal import Decimal, InvalidOperation

from core.exceptions import MargenInvalidoError, ReglaNegocioViolada
from .models import Categoria, Producto


class ProductoService:
    """Servicio de dominio para operaciones de productos."""

    @staticmethod
    def _validar_margen(precio_venta, costo):
        if precio_venta < costo:
            raise MargenInvalidoError("El precio de venta debe ser mayor al costo.")

    @staticmethod
    def _coerce_decimal(value):
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @classmethod
    def crear(cls, data):
        """Crea un producto validando que el margen sea positivo."""
        categoria = data.get("categoria")
        if isinstance(categoria, Categoria):
            categoria_obj = categoria
        else:
            categoria_obj = Categoria.objects.get(pk=categoria)

        precio_venta = cls._coerce_decimal(data["precio_venta"])
        costo = cls._coerce_decimal(data["costo"])
        cls._validar_margen(precio_venta, costo)

        return Producto.objects.create(
            nombre=data.get("nombre", "").strip(),
            categoria=categoria_obj,
            precio_venta=precio_venta,
            costo=costo,
            stock_actual=int(data.get("stock_actual", 0)),
            stock_minimo=int(data.get("stock_minimo", 10)),
            unidad=data.get("unidad", "unidad"),
            codigo_barra=(data.get("codigo_barra", "") or "").strip() or None,
            descripcion=(data.get("descripcion", "") or "").strip() or None,
        )

    @classmethod
    def actualizar(cls, producto, data):
        """Actualiza un producto validando el margen si cambian precio/costo."""
        precio_venta = data.get("precio_venta")
        costo = data.get("costo")

        if precio_venta is not None or costo is not None:
            nuevo_precio = (
                cls._coerce_decimal(precio_venta)
                if precio_venta is not None
                else producto.precio_venta
            )
            nuevo_costo = (
                cls._coerce_decimal(costo)
                if costo is not None
                else producto.costo
            )
            cls._validar_margen(nuevo_precio, nuevo_costo)

        if "nombre" in data:
            producto.nombre = data["nombre"].strip()
        if "categoria" in data:
            categoria = data["categoria"]
            producto.categoria = (
                categoria
                if isinstance(categoria, Categoria)
                else Categoria.objects.get(pk=categoria)
            )
        if precio_venta is not None:
            producto.precio_venta = cls._coerce_decimal(precio_venta)
        if costo is not None:
            producto.costo = cls._coerce_decimal(costo)
        if "stock_actual" in data:
            producto.stock_actual = int(data["stock_actual"])
        if "stock_minimo" in data:
            producto.stock_minimo = int(data["stock_minimo"])
        if "unidad" in data:
            producto.unidad = data["unidad"]
        if "codigo_barra" in data:
            producto.codigo_barra = (data["codigo_barra"] or "").strip() or None
        if "descripcion" in data:
            producto.descripcion = (data["descripcion"] or "").strip() or None
        if "activo" in data:
            producto.activo = bool(data["activo"])

        producto.save()
        return producto

    @staticmethod
    def eliminar(producto):
        """Desactiva un producto (soft delete) conservando su historial."""
        producto.activo = False
        producto.save(update_fields=["activo", "actualizado_en"])
        return producto


class CategoriaService:
    """Servicio de dominio para operaciones de categorías."""

    @staticmethod
    def _validar_nombre_unico(nombre, exclude=None):
        qs = Categoria.objects.filter(nombre__iexact=nombre.strip())
        if exclude is not None:
            qs = qs.exclude(pk=exclude.pk)
        if qs.exists():
            raise ReglaNegocioViolada("Ya existe una categoria con ese nombre.")

    @classmethod
    def crear(cls, nombre, descripcion=None):
        """Crea una categoría validando que el nombre sea único."""
        cls._validar_nombre_unico(nombre)
        return Categoria.objects.create(
            nombre=nombre.strip(),
            descripcion=(descripcion or "").strip() or None,
        )

    @classmethod
    def actualizar(cls, categoria, nombre, descripcion=None):
        """Actualiza una categoría validando unicidad de nombre."""
        cls._validar_nombre_unico(nombre, exclude=categoria)
        categoria.nombre = nombre.strip()
        categoria.descripcion = (descripcion or "").strip() or None
        categoria.save(update_fields=["nombre", "descripcion", "actualizado_en"])
        return categoria

    @staticmethod
    def eliminar(categoria):
        """Desactiva una categoría solo si no tiene productos activos."""
        if categoria.productos.filter(activo=True).exists():
            raise ReglaNegocioViolada(
                "No se puede eliminar una categoria con productos activos."
            )
        categoria.activo = False
        categoria.save(update_fields=["activo", "actualizado_en"])
        return categoria
