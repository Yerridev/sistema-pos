from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .utils import calculate_stats


class InventarioDashboardTests(TestCase):
    def setUp(self):
        self.url = reverse('productos:dashboard')
        self.user_model = get_user_model()

    def _login_user(self, role):
        user = self.user_model.objects.create_user(
            username=f'{role}_user',
            password='password123',
            rol=role,
        )
        self.client.login(username=user.username, password='password123')
        return user

    def test_dashboard_view_requires_login(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_dashboard_view_accessible_to_admin(self):
        self._login_user('admin')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_view_accessible_to_supervisor(self):
        self._login_user('supervisor')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_view_accessible_to_cajero(self):
        self._login_user('cajero')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_stats_calculated_correctly(self):
        productos_data = {
            'count': 3,
            'results': [
                {
                    'precio_venta': '10.00',
                    'stock_actual': 5,
                    'stock_minimo': 3,
                    'categoria_nombre': 'Abarrotes',
                },
                {
                    'precio_venta': '2.50',
                    'stock_actual': 1,
                    'stock_minimo': 5,
                    'categoria_nombre': 'Abarrotes',
                },
                {
                    'precio_venta': '1.00',
                    'stock_actual': 10,
                    'stock_minimo': 2,
                    'categoria_nombre': 'Bebidas',
                },
            ],
        }

        stats = calculate_stats(productos_data)

        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['low_stock_count'], 1)
        self.assertEqual(stats['inventory_value'], Decimal('62.50'))
        self.assertEqual(stats['top_category'], 'Abarrotes')

    def test_edit_button_visible_for_admin(self):
        self._login_user('admin')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Editar', content)
        self.assertIn('Eliminar', content)

    def test_delete_button_hidden_for_cajero(self):
        self._login_user('cajero')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn('Eliminar', content)

    def test_delete_button_hidden_for_supervisor(self):
        self._login_user('supervisor')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertNotIn('Eliminar', content)

    def test_template_renders_inventory_title(self):
        self._login_user('admin')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Inventario', content)
        self.assertIn('Total productos', content)