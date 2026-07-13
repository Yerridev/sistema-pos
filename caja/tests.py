from types import SimpleNamespace

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from caja.models import Caja, MovimientoCaja
from caja.permissions import CanAccessCaja


class CajaPermissionsTests(SimpleTestCase):
    def test_can_access_caja_permission(self):
        permission = CanAccessCaja()
        view = SimpleNamespace()

        req_admin = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='admin', id=1))
        req_cajero = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=2))
        req_other = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='otro', id=3))

        self.assertTrue(permission.has_permission(req_admin, view))
        self.assertTrue(permission.has_permission(req_cajero, view))
        self.assertFalse(permission.has_permission(req_other, view))

    def test_can_access_caja_object(self):
        permission = CanAccessCaja()
        view = SimpleNamespace()
        caja = SimpleNamespace(cajero_id=22)

        req_admin = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='admin', id=1))
        req_owner = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=22))
        req_other = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, rol='cajero', id=9))

        self.assertTrue(permission.has_object_permission(req_admin, view, caja))
        self.assertTrue(permission.has_object_permission(req_owner, view, caja))
        self.assertFalse(permission.has_object_permission(req_other, view, caja))


# ── Golden Tests: comportamiento actual antes del refactor ─────────────────


class CajaAbrirCerrarGoldenTests(TestCase):
    """Golden tests del flujo abrir/cerrar caja vía API (ViewSet)."""

    def setUp(self):
        User = get_user_model()
        self.cajero = User.objects.create_user(
            username='cajero_caja_golden', password='test123', rol='cajero',
        )

    def test_abrir_api_crea_caja_abierta(self):
        """POST /api/cajas/{id}/abrir/ abre la caja con saldo inicial."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)
        caja = Caja.objects.create(
            nombre='Caja Test Abrir', cajero=self.cajero,
            saldo_inicial=Decimal('0.00'), estado='CERRADA',
        )

        response = api.post(f'/api/cajas/{caja.id}/abrir/', {
            'saldo_inicial': '150.00',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        caja.refresh_from_db()
        self.assertEqual(caja.estado, 'ABIERTA')
        self.assertEqual(caja.saldo_inicial, Decimal('150.00'))
        self.assertEqual(caja.cajero, self.cajero)

    def test_abrir_api_rechaja_caja_ya_abierta(self):
        """Abrir una caja ya ABIERTA retorna 400."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)
        caja = Caja.objects.create(
            nombre='Caja Ya Abierta', cajero=self.cajero,
            saldo_inicial=Decimal('50.00'), estado='ABIERTA',
        )

        response = api.post(f'/api/cajas/{caja.id}/abrir/', {
            'saldo_inicial': '100.00',
        }, format='json')

        self.assertEqual(response.status_code, 400)

    def test_cerrar_api_cambia_estado_y_registra_saldo_final(self):
        """POST /api/cajas/{id}/cerrar/ cierra caja y setea saldo_final."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)
        caja = Caja.objects.create(
            nombre='Caja Cerrar', cajero=self.cajero,
            saldo_inicial=Decimal('100.00'), estado='ABIERTA',
        )
        # Agregar un movimiento para que saldo_actual != saldo_inicial
        MovimientoCaja.objects.create(
            caja=caja, tipo='INGRESO', monto=Decimal('50.00'),
            concepto='Venta test', usuario=self.cajero,
        )

        response = api.post(f'/api/cajas/{caja.id}/cerrar/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        caja.refresh_from_db()
        self.assertEqual(caja.estado, 'CERRADA')
        self.assertIsNotNone(caja.saldo_final)
        self.assertEqual(caja.saldo_final, Decimal('150.00'))
        self.assertIsNotNone(caja.fecha_cierre)

    def test_cerrar_api_rechaja_caja_cerrada(self):
        """Cerrar una caja CERRADA retorna 400."""
        from rest_framework.test import APIClient

        api = APIClient()
        api.force_authenticate(user=self.cajero)
        caja = Caja.objects.create(
            nombre='Caja Cerrada', cajero=self.cajero,
            saldo_inicial=Decimal('0.00'), estado='CERRADA',
        )

        response = api.post(f'/api/cajas/{caja.id}/cerrar/', {}, format='json')

        self.assertEqual(response.status_code, 400)
