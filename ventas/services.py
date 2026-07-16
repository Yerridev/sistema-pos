from decimal import Decimal

from django.db import transaction

from caja.models import Caja, MovimientoCaja
from core.descuentos import obtener_politica
from core.exceptions import CajaAjena, CajaNoAbierta, ProductoSinStock, ReglaNegocioViolada, RecursoNoEncontrado, VentaYaAnulada
from productos.models import Producto
from ventas.models import DetalleVenta, Venta


class VentaService:
    """Servicio de dominio para registrar y anular ventas.

    Es la única fuente de verdad para la creación y anulación de ventas;
    las views actúan únicamente como adaptadores delegando aquí.
    """

    @classmethod
    @transaction.atomic
    def registrar(cls, usuario, caja_id, metodo_pago, descuento=None, detalles=None,
                  politica_descuento=None, contexto_descuento=None):
        """Registra una venta, decrementa stock y crea el movimiento de caja.

        Args:
            usuario: instancia de ``Usuario`` que realiza la venta.
            caja_id: identificador de la caja donde se registra la venta.
            metodo_pago: método de pago (EFECTIVO/TARJETA/TRANSFERENCIA).
            descuento: descuento global fijo aplicado a la venta. Se ignora si
                se indica ``politica_descuento``.
            detalles: lista de diccionarios con ``producto``, ``cantidad``,
                ``precio_unitario`` y ``descuento_linea``.
            politica_descuento: nombre de la política de descuento a aplicar
                (Strategy Pattern). Si se indica, el descuento se calcula con
                ``core.descuentos.obtener_politica`` sobre el importe total.
            contexto_descuento: diccionario con datos para la política
                (porcentaje, cantidad_total, es_cliente_frecuente, etc.).

        Raises:
            RecursoNoEncontrado: si la caja no existe.
            CajaNoAbierta: si la caja no está ABIERTA.
            CajaAjena: si la caja pertenece a otro cajero y el usuario no es admin.
            ReglaNegocioViolada: si los detalles están vacíos, el descuento es
                negativo o supera el importe total.
            ProductoSinStock: si algún producto no tiene stock suficiente.
            ValueError: si ``politica_descuento`` no corresponde a una política
                registrada.
        """
        # Con Strategy Pattern el descuento se calcula tras conocer el importe
        # total; sin política se usa el descuento fijo recibido.
        if politica_descuento is None:
            if descuento is None:
                descuento = Decimal("0.00")
            else:
                descuento = Decimal(str(descuento))
            if descuento < 0:
                raise ReglaNegocioViolada("El descuento no puede ser negativo.")

        if not detalles:
            raise ReglaNegocioViolada("Debe enviar al menos un detalle.")

        try:
            caja = Caja.objects.select_for_update().get(pk=caja_id)
        except Caja.DoesNotExist as exc:
            raise RecursoNoEncontrado(f"La caja {caja_id} no existe.") from exc

        if caja.estado != "ABIERTA":
            raise CajaNoAbierta("La caja debe estar ABIERTA para registrar ventas.")
        if caja.cajero_id != usuario.id and getattr(usuario, "rol", None) != "admin":
            raise CajaAjena("No puede vender en una caja de otro cajero.")

        # Primera pasada: validar datos y calcular importe total.
        importe_total = Decimal("0.00")
        lineas_validadas = []
        for item in detalles:
            producto = item["producto"]
            if isinstance(producto, Producto):
                producto_id = producto.id
            else:
                producto_id = int(producto)

            cantidad = int(item["cantidad"])
            if cantidad <= 0:
                raise ReglaNegocioViolada("La cantidad debe ser mayor que cero.")

            precio_unitario = item.get("precio_unitario")
            if precio_unitario is None:
                precio_linea = None
            else:
                precio_linea = Decimal(str(precio_unitario))

            descuento_linea = item.get("descuento_linea", Decimal("0.00"))
            if descuento_linea is None:
                descuento_linea = Decimal("0.00")
            else:
                descuento_linea = Decimal(str(descuento_linea))

            if descuento_linea < 0:
                raise ReglaNegocioViolada("El descuento de línea no puede ser negativo.")

            try:
                producto = Producto.objects.select_for_update().get(pk=producto_id, activo=True)
            except Producto.DoesNotExist as exc:
                raise RecursoNoEncontrado(f"El producto {producto_id} no existe.") from exc

            precio_efectivo = producto.precio_venta if precio_linea is None else precio_linea
            subtotal_linea = (precio_efectivo * cantidad) - descuento_linea
            if descuento_linea > (precio_efectivo * cantidad):
                raise ReglaNegocioViolada(
                    "El descuento de línea no puede superar el subtotal de la línea."
                )

            if producto.stock_actual < cantidad:
                raise ProductoSinStock(
                    f"Stock insuficiente para {producto.nombre}. "
                    f"Disponible: {producto.stock_actual}."
                )

            importe_total += subtotal_linea
            lineas_validadas.append({
                "producto": producto,
                "cantidad": cantidad,
                "precio_unitario": precio_efectivo,
                "descuento_linea": descuento_linea,
            })

        # Strategy Pattern: la política calcula el descuento sobre el importe
        # total ya validado. Las políticas nunca retornan valores negativos.
        if politica_descuento is not None:
            politica = obtener_politica(politica_descuento)
            descuento = politica.calcular(importe_total, contexto_descuento or {})

        if descuento > importe_total:
            raise ReglaNegocioViolada(
                "El descuento global no puede superar el importe total de la venta."
            )

        venta = Venta.objects.create(
            cajero=usuario,
            caja=caja,
            metodo_pago=metodo_pago,
            descuento=descuento,
            creado_por=usuario,
        )

        productos_actualizar = []
        for linea in lineas_validadas:
            DetalleVenta.objects.create(
                venta=venta,
                producto=linea["producto"],
                cantidad=linea["cantidad"],
                precio_unitario=linea["precio_unitario"],
                descuento_linea=linea["descuento_linea"],
            )
            linea["producto"].stock_actual -= linea["cantidad"]
            productos_actualizar.append(linea["producto"])

        Producto.objects.bulk_update(productos_actualizar, ["stock_actual"])
        venta.calcular_totales()

        MovimientoCaja.objects.create(
            caja=caja,
            tipo="INGRESO",
            monto=venta.total,
            concepto=f"Venta #{venta.id}",
            usuario=usuario,
        )
        return venta

    @classmethod
    @transaction.atomic
    def anular(cls, venta, usuario, motivo, restaurar_stock=True):
        """Anula una venta, restaura stock opcionalmente y crea egreso en caja.

        Args:
            venta: instancia de ``Venta`` a anular.
            usuario: usuario que realiza la anulación.
            motivo: motivo de la anulación.
            restaurar_stock: si es ``True`` devuelve el stock al inventario.

        Raises:
            VentaYaAnulada: si la venta ya se encuentra anulada.
        """
        if venta.estado == "ANULADA":
            raise VentaYaAnulada("La venta ya está anulada.")

        venta.anular(motivo, usuario)

        if restaurar_stock:
            productos_actualizar = []
            for detalle in DetalleVenta.objects.select_related("producto").filter(venta=venta):
                detalle.producto.stock_actual += detalle.cantidad
                productos_actualizar.append(detalle.producto)
            Producto.objects.bulk_update(productos_actualizar, ["stock_actual"])

        MovimientoCaja.objects.create(
            caja=venta.caja,
            tipo="EGRESO",
            monto=venta.total,
            concepto=f"Anulacion venta #{venta.id}: {motivo}",
            usuario=usuario,
        )
        return venta
