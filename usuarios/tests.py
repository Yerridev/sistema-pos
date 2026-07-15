from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class UsuarioListContextTests(TestCase):
    def setUp(self):
        self.url = reverse('usuarios:list')
        self.user_model = get_user_model()

    def _login_admin(self):
        return self.user_model.objects.create_user(
            username='admin_ctx_user',
            password='password123',
            rol='admin',
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_non_admin_is_forbidden(self):
        cajero = self.user_model.objects.create_user(
            username='cajero_ctx_user',
            password='password123',
            rol='cajero',
        )
        self.client.login(username='cajero_ctx_user', password='password123')
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_context_has_page_title_and_active_nav(self):
        self._login_admin()
        self.client.login(username='admin_ctx_user', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_title'], 'Usuarios')
        self.assertEqual(response.context['active_nav'], 'usuarios:list')