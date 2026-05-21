from types import SimpleNamespace

from django.test import SimpleTestCase

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
