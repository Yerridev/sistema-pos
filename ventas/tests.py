from types import SimpleNamespace

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from caja.models import Caja
from productos.models import Categoria, Producto
from ventas.models import DetalleVenta, Venta
from ventas.permissions import CanAccessVentaObject, CanAnularVenta, IsCajeroOrAdmin
from ventas.serializers import VentaCreateSerializer


class VentasPermissionsTests(SimpleTestCase):
    def test_is_cajero_or_admin_allows_admin_and_cajero(self):
        permission = IsCajeroOrAdmin()
        view = SimpleNamespace()

        req_admin = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='admin'))
        req_cajero = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero'))
        req_other = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='otro'))

        self.assertTrue(permission.has_permission(req_admin, view))
        self.assertTrue(permission.has_permission(req_cajero, view))
        self.assertFalse(permission.has_permission(req_other, view))

    def test_can_access_venta_object(self):
        permission = CanAccessVentaObject()
        view = SimpleNamespace()
        venta = SimpleNamespace(cajero_id=10)

        req_admin = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='admin', id=1))
        req_owner = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=10))
        req_other = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=99))

        self.assertTrue(permission.has_object_permission(req_admin, view, venta))
        self.assertTrue(permission.has_object_permission(req_owner, view, venta))
        self.assertFalse(permission.has_object_permission(req_other, view, venta))

    def test_can_anular_venta_only_owner_or_admin_when_action_is_anular(self):
        permission = CanAnularVenta()
        view = SimpleNamespace(action='anular')
        venta = SimpleNamespace(cajero_id=4)

        req_admin = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='admin', id=1))
        req_owner = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=4))
        req_other = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=8))

        self.assertTrue(permission.has_object_permission(req_admin, view, venta))
        self.assertTrue(permission.has_object_permission(req_owner, view, venta))
        self.assertFalse(permission.has_object_permission(req_other, view, venta))


class VentaCreateSerializerTests(SimpleTestCase):
    def test_requires_caja(self):
        request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=1))
        serializer = VentaCreateSerializer(
            data={
                'metodo_pago': 'EFECTIVO',
                'descuento': '0.00',
                'detalles': [],
            },
            context={'request': request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('caja_id', serializer.errors)


class VentaTotalesPeruTests(TestCase):
    def test_calcular_totales_desglosa_igv_incluido_en_precio(self):
        user = get_user_model().objects.create_user(username='cajero', password='test123', rol='cajero')
        caja = Caja.objects.create(nombre='Caja 1', cajero=user, saldo_inicial=Decimal('0.00'))
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(
            nombre='Gaseosa',
            categoria=categoria,
            precio_venta=Decimal('118.00'),
            costo=Decimal('80.00'),
            stock_actual=10,
        )
        venta = Venta.objects.create(cajero=user, caja=caja, metodo_pago='EFECTIVO')
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=1,
            precio_unitario=producto.precio_venta,
        )

        venta.calcular_totales()

        self.assertEqual(venta.subtotal, Decimal('100.00'))
        self.assertEqual(venta.igv, Decimal('18.00'))
        self.assertEqual(venta.total, Decimal('118.00'))
