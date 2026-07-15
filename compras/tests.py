from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from compras.models import Compra, DetalleCompra, Proveedor
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
