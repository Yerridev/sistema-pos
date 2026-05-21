from types import SimpleNamespace

from django.test import SimpleTestCase

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
