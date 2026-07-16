import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from caja.models import Caja, MovimientoCaja
from compras.models import Compra, DetalleCompra, Proveedor
from productos.models import Producto
from ventas.models import DetalleVenta, Venta


class Command(BaseCommand):
    help = "Genera datos completos para reportes: proveedores, compras, cajas, ventas (7 días)."

    def handle(self, *args, **options):
        User = get_user_model()
        ahora = timezone.now()

        admin = User.objects.get(username="admin")
        cajero = User.objects.get(username="cajero")
        productos = list(Producto.objects.filter(activo=True))
        if not productos:
            self.stderr.write("No hay productos. Ejecutá seed_data primero.")
            return

        proveedores_data = [
            ("Distribuidora Lima SAC", "20512345678", "Carlos Pérez"),
            ("Alicorp Peru S.A.", "20698765432", "María López"),
            ("Industrias Alimenticias SAC", "20455566677", "Juan García"),
            ("Importaciones Express", "20333444555", "Ana Torres"),
        ]
        proveedores = []
        for nombre, ruc, contacto in proveedores_data:
            prov, _ = Proveedor.objects.get_or_create(
                ruc=ruc, defaults={"nombre": nombre, "contacto": contacto}
            )
            proveedores.append(prov)
        self.stdout.write(f"{len(proveedores)} proveedores creados.")

        compras_creadas = 0
        for dias_atras in range(7, -1, -1):
            fecha_base = ahora - timedelta(days=dias_atras)
            num_compras = random.randint(1, 2)
            for _ in range(num_compras):
                prov = random.choice(proveedores)
                fecha_compra = fecha_base.replace(
                    hour=random.randint(8, 14),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59),
                )
                compra = Compra.objects.create(
                    proveedor=prov,
                    fecha=fecha_compra,
                    estado="REGISTRADA",
                )
                num_detalles = random.randint(2, 5)
                productos_compra = random.sample(productos, min(num_detalles, len(productos)))
                for prod in productos_compra:
                    cantidad = random.randint(10, 50)
                    costo = prod.costo
                    DetalleCompra.objects.create(
                        compra=compra,
                        producto=prod,
                        cantidad=cantidad,
                        costo_unitario=costo,
                    )
                compra.calcular_total()
                compras_creadas += 1
        self.stdout.write(f"{compras_creadas} compras creadas.")

        cajas_creadas = 0
        ventas_creadas = 0
        for dias_atras in range(7, -1, -1):
            fecha_base = ahora - timedelta(days=dias_atras)
            fecha_apertura = fecha_base.replace(
                hour=8, minute=0, second=0, microsecond=0
            )
            fecha_cierre = fecha_base.replace(
                hour=17, minute=30, second=0, microsecond=0
            )
            saldo_inicial = Decimal("200.00")
            caja = Caja.objects.create(
                nombre=f"Caja Principal {fecha_base.strftime('%d/%m')}",
                saldo_inicial=saldo_inicial,
                fecha_apertura=fecha_apertura,
                cajero=cajero,
                estado="CERRADA" if fecha_cierre < ahora else "ABIERTA",
                fecha_cierre=fecha_cierre if fecha_cierre < ahora else None,
            )
            cajas_creadas += 1

            MovimientoCaja.objects.create(
                caja=caja,
                tipo="INGRESO",
                monto=saldo_inicial,
                concepto="Fondo inicial de caja",
                fecha=fecha_apertura,
                usuario=admin,
            )

            num_ventas = random.randint(5, 12)
            total_ventas_dia = Decimal("0.00")
            for i in range(num_ventas):
                venta_hora = random.randint(9, 16)
                venta_minuto = random.randint(0, 59)
                fecha_venta = fecha_base.replace(
                    hour=venta_hora, minute=venta_minuto, second=random.randint(0, 59)
                )
                metodo_pago = random.choice(["EFECTIVO", "TARJETA", "TRANSFERENCIA"])
                estado = "COMPLETADA"
                motivo = None
                if random.random() < 0.08:
                    estado = "ANULADA"
                    motivo = random.choice([
                        "Cliente se arrepintió",
                        "Error en precio",
                        "Producto dañado",
                    ])

                venta = Venta(
                    cajero=cajero,
                    caja=caja,
                    fecha=fecha_venta,
                    metodo_pago=metodo_pago,
                    estado=estado,
                    motivo_anulacion=motivo,
                    anulado_por=admin if estado == "ANULADA" else None,
                    fecha_anulacion=fecha_venta if estado == "ANULADA" else None,
                )
                venta.save()

                num_items = random.randint(1, 4)
                items_venta = random.sample(productos, min(num_items, len(productos)))
                for prod in items_venta:
                    cantidad = random.randint(1, 3)
                    descuento = Decimal("0.00")
                    if random.random() < 0.2:
                        descuento = Decimal(str(round(random.uniform(0.50, 3.00), 2)))
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=prod,
                        cantidad=cantidad,
                        precio_unitario=prod.precio_venta,
                        descuento_linea=descuento,
                    )

                venta.calcular_totales()
                total_ventas_dia += venta.total
                ventas_creadas += 1

            if total_ventas_dia > 0:
                MovimientoCaja.objects.create(
                    caja=caja,
                    tipo="INGRESO",
                    monto=total_ventas_dia,
                    concepto=f"Ventas del día - {num_ventas} tickets",
                    fecha=fecha_cierre - timedelta(minutes=5),
                    usuario=cajero,
                )

            gasto_fijo = Decimal("35.00")
            MovimientoCaja.objects.create(
                caja=caja,
                tipo="EGRESO",
                monto=gasto_fijo,
                concepto="Gastos varios del día",
                fecha=fecha_cierre - timedelta(minutes=10),
                usuario=cajero,
            )

        self.stdout.write(f"{cajas_creadas} cajas creadas.")
        self.stdout.write(f"{ventas_creadas} ventas creadas.")
        self.stdout.write(self.style.SUCCESS("Seed completo. Datos listos para reportes."))
