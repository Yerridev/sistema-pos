from types import SimpleNamespace

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from caja.models import Caja, MovimientoCaja
from caja.permissions import CanAccessCaja
from caja.services import CajaService
from core.exceptions import CajaAjena, CajaNoAbierta, CajaYaAbierta, ReglaNegocioViolada


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


class CajaServiceTests(TestCase):
    """Tests unitarios de dominio para CajaService."""

    def setUp(self):
        User = get_user_model()
        self.cajero = User.objects.create_user(
            username='cajero_service', password='test123', rol='cajero',
        )
        self.otro_cajero = User.objects.create_user(
            username='otro_cajero', password='test123', rol='cajero',
        )
        self.admin = User.objects.create_user(
            username='admin_service', password='test123', rol='admin',
        )

    def test_abrir_crea_caja_abierta(self):
        """abrir() crea una caja con estado ABIERTA y los datos correctos."""
        caja = CajaService.abrir(
            usuario=self.cajero,
            nombre='Caja Apertura',
            saldo_inicial=Decimal('250.00'),
        )

        self.assertIsInstance(caja, Caja)
        self.assertEqual(caja.nombre, 'Caja Apertura')
        self.assertEqual(caja.saldo_inicial, Decimal('250.00'))
        self.assertEqual(caja.estado, 'ABIERTA')
        self.assertEqual(caja.cajero, self.cajero)
        self.assertTrue(caja.esta_abierta)

    def test_abrir_con_caja_abierta_levanta_excepcion(self):
        """abrir() falla si el cajero ya tiene una caja ABIERTA."""
        CajaService.abrir(self.cajero, 'Primera', Decimal('100.00'))

        with self.assertRaises(CajaYaAbierta):
            CajaService.abrir(self.cajero, 'Segunda', Decimal('50.00'))

        self.assertEqual(Caja.objects.filter(cajero=self.cajero).count(), 1)

    def test_cerrar_calcula_saldo_final_y_cierra(self):
        """cerrar() persiste saldo_actual en saldo_final y estado CERRADA."""
        caja = CajaService.abrir(self.cajero, 'Caja Cierre', Decimal('100.00'))
        MovimientoCaja.objects.create(
            caja=caja, tipo='INGRESO', monto=Decimal('75.00'),
            concepto='Ingreso test', usuario=self.cajero,
        )

        cerrada = CajaService.cerrar(caja=caja, usuario=self.cajero)

        self.assertEqual(cerrada.estado, 'CERRADA')
        self.assertEqual(cerrada.saldo_final, Decimal('175.00'))
        self.assertIsNotNone(cerrada.fecha_cierre)
        caja.refresh_from_db()
        self.assertEqual(caja.estado, 'CERRADA')

    def test_cerrar_caja_cerrada_levanta_regla_negocio(self):
        """cerrar() sobre una caja CERRADA lanza ReglaNegocioViolada."""
        caja = CajaService.abrir(self.cajero, 'Caja Cerrada', Decimal('0.00'))
        CajaService.cerrar(caja=caja, usuario=self.cajero)

        with self.assertRaises(ReglaNegocioViolada):
            CajaService.cerrar(caja=caja, usuario=self.cajero)

    def test_cerrar_caja_ajena_levanta_excepcion(self):
        """Solo el propietario o admin pueden cerrar una caja."""
        caja = CajaService.abrir(self.cajero, 'Caja Ajena', Decimal('0.00'))

        with self.assertRaises(CajaAjena):
            CajaService.cerrar(caja=caja, usuario=self.otro_cajero)

    def test_registrar_movimiento_crea_registro(self):
        """registrar_movimiento() crea un MovimientoCaja con los datos enviados."""
        caja = CajaService.abrir(self.cajero, 'Caja Movimiento', Decimal('0.00'))

        movimiento = CajaService.registrar_movimiento(
            caja=caja,
            usuario=self.cajero,
            tipo='INGRESO',
            monto=Decimal('120.00'),
            concepto='Venta contado',
        )

        self.assertIsInstance(movimiento, MovimientoCaja)
        self.assertEqual(movimiento.caja, caja)
        self.assertEqual(movimiento.tipo, 'INGRESO')
        self.assertEqual(movimiento.monto, Decimal('120.00'))
        self.assertEqual(movimiento.concepto, 'Venta contado')
        self.assertEqual(movimiento.usuario, self.cajero)

    def test_registrar_movimiento_en_caja_cerrada_levanta_excepcion(self):
        """registrar_movimiento() requiere una caja ABIERTA."""
        caja = CajaService.abrir(self.cajero, 'Caja Cerrada', Decimal('0.00'))
        CajaService.cerrar(caja=caja, usuario=self.cajero)

        with self.assertRaises(CajaNoAbierta):
            CajaService.registrar_movimiento(
                caja=caja, usuario=self.cajero,
                tipo='INGRESO', monto=Decimal('10.00'), concepto='x',
            )

    def test_registrar_movimiento_caja_ajena_levanta_excepcion(self):
        """Solo el propietario o admin registran movimientos en una caja."""
        caja = CajaService.abrir(self.cajero, 'Caja Ajena', Decimal('0.00'))

        with self.assertRaises(CajaAjena):
            CajaService.registrar_movimiento(
                caja=caja, usuario=self.otro_cajero,
                tipo='INGRESO', monto=Decimal('10.00'), concepto='x',
            )
