from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ReportesDashboardContextTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin_reportes_ctx', password='password123', rol='admin',
        )
        self.client.login(username='admin_reportes_ctx', password='password123')
        self.url = reverse('reportes:dashboard')

    def test_context_has_page_title_and_active_nav(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_title'], 'Reportes')
        self.assertEqual(response.context['active_nav'], 'reportes:dashboard')

    def test_non_admin_is_forbidden(self):
        User = get_user_model()
        cajero = User.objects.create_user(
            username='cajero_reportes_ctx', password='password123', rol='cajero',
        )
        self.client.login(username='cajero_reportes_ctx', password='password123')
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))