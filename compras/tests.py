from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from compras.models import Compra, DetalleCompra, Proveedor
from compras.services import CompraService
from core.exceptions import ReglaNegocioViolada
from productos.models import Categoria, Producto


# ── Golden Tests: comportamiento actual antes del refactor ─────────────────


class CompraRegistrarGoldenTests(TestCase):
    """Golden tests del flujo de registro de compra vía API (ViewSet)."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin_compra_golden', password='test123', rol='admin',
        )
        self.proveedor = Proveedor.objects.create(
            nombre='Proveedor Golden', ruc='12345678901', contacto='Juan',
        )
        self.categoria = Categoria.objects.create(nombre='Compra Cat Golden')
        self.producto = Producto.objects.create(
            nombre='Producto Compra',
            categoria=self.categoria,
            precio_venta=Decimal('20.00'),
            costo=Decimal('10.00'),
            stock_actual=15,
        )

    def test_compra_api_incrementa_stock_y_actualiza_costo(self):
        """POST /api/compras/ crea compra, incrementa stock, actualiza costo."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.admin)

        stock_antes = self.producto.stock_actual
        costo_antes = self.producto.costo

        response = api.post('/api/compras/', {
            'proveedor': self.proveedor.id,
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 25,
                'costo_unitario': '12.50',
            }],
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_antes + 25)
        self.assertEqual(self.producto.costo, Decimal('12.50'))
        self.assertNotEqual(self.producto.costo, costo_antes)

    def test_compra_api_calcula_total(self):
        """La compra calcula el total automáticamente."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.admin)

        response = api.post('/api/compras/', {
            'proveedor': self.proveedor.id,
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 10,
                'costo_unitario': '8.00',
            }],
        }, format='json')

        compra = Compra.objects.get(id=response.data['id'])
        self.assertEqual(compra.total, Decimal('80.00'))
        self.assertEqual(compra.estado, 'REGISTRADA')
        self.assertEqual(compra.detalles.count(), 1)

    def test_compra_api_rechaza_cantidad_invalida(self):
        """Cantidad <= 0 retorna 400."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.admin)

        response = api.post('/api/compras/', {
            'proveedor': self.proveedor.id,
            'detalles': [{
                'producto': self.producto.id,
                'cantidad': 0,
                'costo_unitario': '5.00',
            }],
        }, format='json')

        self.assertEqual(response.status_code, 400)


# ── Tests: CompraService ----------------------------------------------------


class CompraServiceTests(TestCase):
    """Tests unitarios del servicio de registro de compras."""

    def setUp(self):
        self.proveedor = Proveedor.objects.create(
            nombre='Proveedor Service', ruc='98765432109', contacto='Luis',
        )
        self.categoria = Categoria.objects.create(nombre='Service Cat')
        self.producto = Producto.objects.create(
            nombre='Producto Service',
            categoria=self.categoria,
            precio_venta=Decimal('25.00'),
            costo=Decimal('10.00'),
            stock_actual=15,
        )

    def test_registrar_crea_compra_con_total_correcto(self):
        """El service crea la compra y calcula el total por los detalles."""
        compra = CompraService.registrar(
            self.proveedor,
            [{
                'producto': self.producto,
                'cantidad': 10,
                'costo_unitario': Decimal('5.00'),
            }],
        )

        self.assertEqual(compra.proveedor, self.proveedor)
        self.assertEqual(compra.total, Decimal('50.00'))
        self.assertEqual(compra.estado, 'REGISTRADA')
        self.assertEqual(compra.detalles.count(), 1)
        self.assertEqual(compra.detalles.first().subtotal, Decimal('50.00'))

    def test_registrar_incrementa_stock(self):
        """El service incrementa el stock_actual del producto."""
        stock_antes = self.producto.stock_actual

        CompraService.registrar(
            self.proveedor,
            [{
                'producto': self.producto,
                'cantidad': 20,
                'costo_unitario': Decimal('6.00'),
            }],
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_antes + 20)

    def test_registrar_actualiza_costo(self):
        """El service actualiza producto.costo con el costo_unitario del detalle."""
        CompraService.registrar(
            self.proveedor,
            [{
                'producto': self.producto,
                'cantidad': 5,
                'costo_unitario': Decimal('7.50'),
            }],
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.costo, Decimal('7.50'))

    def test_registrar_cantidad_invalida_lanza_regla_negocio(self):
        """Cantidad menor o igual a cero lanza ReglaNegocioViolada."""
        with self.assertRaises(ReglaNegocioViolada):
            CompraService.registrar(
                self.proveedor,
                [{
                    'producto': self.producto,
                    'cantidad': 0,
                    'costo_unitario': Decimal('5.00'),
                }],
            )

    def test_registrar_multiples_detalles(self):
        """Varios detalles crean todas las filas y actualizan cada stock."""
        producto2 = Producto.objects.create(
            nombre='Producto Service 2',
            categoria=self.categoria,
            precio_venta=Decimal('30.00'),
            costo=Decimal('8.00'),
            stock_actual=10,
        )

        compra = CompraService.registrar(
            self.proveedor,
            [
                {
                    'producto': self.producto,
                    'cantidad': 5,
                    'costo_unitario': Decimal('2.00'),
                },
                {
                    'producto': producto2,
                    'cantidad': 3,
                    'costo_unitario': Decimal('10.00'),
                },
            ],
        )

        self.assertEqual(Compra.objects.count(), 1)
        self.assertEqual(compra.detalles.count(), 2)
        self.producto.refresh_from_db()
        producto2.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 20)
        self.assertEqual(producto2.stock_actual, 13)
        self.assertEqual(compra.total, Decimal('40.00'))
