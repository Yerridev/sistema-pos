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


# ── Golden Tests: comportamiento actual antes del refactor ─────────────────
# Estos tests capturan el comportamiento EXISTENTE de creación y anulación
# de ventas para que el refactor a VentaService no rompa nada.


class VentaCreateGoldenTests(TestCase):
    """Golden tests del flujo de creación de venta vía API (ViewSet)."""

    def setUp(self):
        User = get_user_model()
        self.cajero = User.objects.create_user(
            username='cajero_golden', password='test123', rol='cajero',
        )
        self.caja = Caja.objects.create(
            nombre='Caja Golden', cajero=self.cajero, saldo_inicial=Decimal('100.00'),
            estado='ABIERTA',
        )
        self.categoria = Categoria.objects.create(nombre='Abarrotes Golden')
        self.producto = Producto.objects.create(
            nombre='Arroz 1kg',
            categoria=self.categoria,
            precio_venta=Decimal('11.80'),
            costo=Decimal('7.00'),
            stock_actual=20,
        )
        self.client.login(username='cajero_golden', password='test123')

    def test_venta_api_crea_venta_y_decrementa_stock(self):
        """POST /api/ventas/ crea venta, DetalleVenta, decrementa stock."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)

        stock_antes = self.producto.stock_actual
        response = api.post('/api/ventas/', {
            'caja_id': self.caja.id,
            'metodo_pago': 'EFECTIVO',
            'descuento': '0.00',
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 3,
                'precio_unitario': str(self.producto.precio_venta),
            }],
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_antes - 3)

        venta = Venta.objects.get(id=response.data['id'])
        self.assertEqual(venta.estado, 'COMPLETADA')
        self.assertEqual(venta.cajero, self.cajero)
        self.assertEqual(venta.caja, self.caja)
        self.assertEqual(venta.detalles.count(), 1)

    def test_venta_api_crea_movimiento_caja_ingreso(self):
        """La venta crea un MovimientoCaja de tipo INGRESO por el total."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)

        movimientos_antes = self.caja.movimientos.count()
        api.post('/api/ventas/', {
            'caja_id': self.caja.id,
            'metodo_pago': 'EFECTIVO',
            'descuento': '0.00',
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 1,
                'precio_unitario': str(self.producto.precio_venta),
            }],
        }, format='json')

        self.caja.refresh_from_db()
        self.assertEqual(self.caja.movimientos.count(), movimientos_antes + 1)
        movimiento = self.caja.movimientos.latest('fecha')
        self.assertEqual(movimiento.tipo, 'INGRESO')
        self.assertEqual(movimiento.usuario, self.cajero)

    def test_venta_api_calcula_totales_con_igv(self):
        """Los totales se calculan con IGV incluido (factor 1.18)."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)

        # 3 unidades × S/. 11.80 = S/. 35.40 (total con IGV)
        # subtotal = 35.40 / 1.18 = 30.00, igv = 5.40
        response = api.post('/api/ventas/', {
            'caja_id': self.caja.id,
            'metodo_pago': 'EFECTIVO',
            'descuento': '0.00',
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 3,
                'precio_unitario': str(self.producto.precio_venta),
            }],
        }, format='json')

        venta = Venta.objects.get(id=response.data['id'])
        self.assertEqual(venta.total, Decimal('35.40'))
        self.assertEqual(venta.subtotal, Decimal('30.00'))
        self.assertEqual(venta.igv, Decimal('5.40'))

    def test_venta_api_rechaza_stock_insuficiente(self):
        """Stock insuficiente retorna 400 y no crea venta ni decrementa."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)

        stock_antes = self.producto.stock_actual
        response = api.post('/api/ventas/', {
            'caja_id': self.caja.id,
            'metodo_pago': 'EFECTIVO',
            'descuento': '0.00',
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 999,
                'precio_unitario': str(self.producto.precio_venta),
            }],
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_antes)
        self.assertEqual(Venta.objects.filter(cajero=self.cajero).count(), 0)

    def test_venta_api_rechaza_caja_cerrada(self):
        """Caja CERRADA retorna 400."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)
        self.caja.estado = 'CERRADA'
        self.caja.save()

        response = api.post('/api/ventas/', {
            'caja_id': self.caja.id,
            'metodo_pago': 'EFECTIVO',
            'descuento': '0.00',
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 1,
                'precio_unitario': str(self.producto.precio_venta),
            }],
        }, format='json')

        self.assertEqual(response.status_code, 400)

    def test_venta_dashboard_crea_venta_y_decrementa_stock(self):
        """POST /dashboard/ventas/nueva/ crea venta via dashboard y decrementa stock."""
        import json

        stock_antes = self.producto.stock_actual
        response = self.client.post('/dashboard/ventas/nueva/', {
            'caja': self.caja.id,
            'metodo_pago': 'EFECTIVO',
            'descuento': '0.00',
            'cart_items': json.dumps([
                {'producto_id': self.producto.id, 'cantidad': 2},
            ]),
        })

        self.assertIn(response.status_code, (302, 200))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_antes - 2)


class VentaAnularGoldenTests(TestCase):
    """Golden tests del flujo de anulación de venta vía API."""

    def setUp(self):
        User = get_user_model()
        self.cajero = User.objects.create_user(
            username='cajero_anular', password='test123', rol='cajero',
        )
        self.caja = Caja.objects.create(
            nombre='Caja Anular', cajero=self.cajero, saldo_inicial=Decimal('0.00'),
            estado='ABIERTA',
        )
        self.categoria = Categoria.objects.create(nombre='Anular Cat')
        self.producto = Producto.objects.create(
            nombre='Producto Anular',
            categoria=self.categoria,
            precio_venta=Decimal('11.80'),
            costo=Decimal('5.00'),
            stock_actual=10,
        )
        # Crear venta inicial
        self.venta = Venta.objects.create(
            cajero=self.cajero, caja=self.caja, metodo_pago='EFECTIVO',
        )
        DetalleVenta.objects.create(
            venta=self.venta, producto=self.producto,
            cantidad=4, precio_unitario=self.producto.precio_venta,
        )
        self.venta.calcular_totales()
        self.producto.stock_actual -= 4
        self.producto.save()

    def test_anular_api_cambia_estado_y_restaura_stock(self):
        """POST /api/ventas/{id}/anular/ anula y restaura stock."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)

        stock_antes = self.producto.stock_actual
        response = api.post(f'/api/ventas/{self.venta.id}/anular/', {
            'motivo': 'Error de registro',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.estado, 'ANULADA')
        self.assertEqual(self.venta.motivo_anulacion, 'Error de registro')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_antes + 4)

    def test_anular_api_crea_movimiento_egreso(self):
        """La anulación crea un MovimientoCaja de tipo EGRESO."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)

        movimientos_antes = self.caja.movimientos.count()
        api.post(f'/api/ventas/{self.venta.id}/anular/', {
            'motivo': 'Test egreso',
        }, format='json')

        self.assertEqual(self.caja.movimientos.count(), movimientos_antes + 1)
        movimiento = self.caja.movimientos.latest('fecha')
        self.assertEqual(movimiento.tipo, 'EGRESO')

    def test_anular_api_rechaza_venta_ya_anulada(self):
        """Anular una venta ya anulada retorna 400."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)

        api.post(f'/api/ventas/{self.venta.id}/anular/', {
            'motivo': 'Primera anulación',
        }, format='json')

        response = api.post(f'/api/ventas/{self.venta.id}/anular/', {
            'motivo': 'Segunda anulación',
        }, format='json')

        self.assertEqual(response.status_code, 400)
