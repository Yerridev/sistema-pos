from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.exceptions import MargenInvalidoError, ReglaNegocioViolada
from .cache import get_cached_productos, invalidate_productos_cache, set_cached_productos
from .models import Categoria, Producto
from .services import CategoriaService, ProductoService
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


class InventarioContextTests(TestCase):
    def setUp(self):
        self.url = reverse('productos:dashboard')
        self.user_model = get_user_model()

    def _login_user(self, role):
        user = self.user_model.objects.create_user(
            username=f'{role}_ctx_user',
            password='password123',
            rol=role,
        )
        self.client.login(username=user.username, password='password123')
        return user

    def test_context_has_page_title_and_active_nav(self):
        self._login_user('admin')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_title'], 'Inventario')
        self.assertEqual(response.context['active_nav'], 'productos:dashboard')


class ProductosDashboardApiTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.categoria = Categoria.objects.create(nombre='Bebidas')
        self.producto = ProductoService.crear({
            'nombre': 'Gaseosa',
            'categoria': self.categoria.id,
            'precio_venta': '3.00',
            'costo': '2.00',
        })

    def _login_user(self, role):
        user = self.user_model.objects.create_user(
            username=f'{role}_user',
            password='password123',
            rol=role,
        )
        self.client.login(username=user.username, password='password123')
        return user

    def test_admin_crea_producto(self):
        self._login_user('admin')
        url = reverse('productos:producto_crear')
        payload = {
            'nombre': 'Agua',
            'categoria': self.categoria.id,
            'precio_venta': '2.00',
            'costo': '1.00',
            'stock_actual': '10',
            'stock_minimo': '2',
        }

        response = self.client.post(url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertTrue(Producto.objects.filter(nombre='Agua').exists())

    def test_crear_producto_con_margen_invalido_devuelve_400(self):
        self._login_user('admin')
        url = reverse('productos:producto_crear')
        payload = {
            'nombre': 'Agua',
            'categoria': self.categoria.id,
            'precio_venta': '1.00',
            'costo': '2.00',
        }

        response = self.client.post(url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_cajero_no_puede_crear_producto(self):
        self._login_user('cajero')
        url = reverse('productos:producto_crear')
        response = self.client.post(url, data={}, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_admin_actualiza_producto(self):
        self._login_user('admin')
        url = reverse('productos:producto_editar', args=[self.producto.pk])
        payload = {
            'nombre': 'Gaseosa Zero',
            'categoria': self.categoria.id,
            'precio_venta': '3.50',
            'costo': '2.00',
        }

        response = self.client.post(url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Gaseosa Zero')

    def test_actualizar_producto_con_margen_invalido_devuelve_400(self):
        self._login_user('admin')
        url = reverse('productos:producto_editar', args=[self.producto.pk])
        payload = {'precio_venta': '1.00'}

        response = self.client.post(url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_admin_elimina_producto(self):
        self._login_user('admin')
        url = reverse('productos:producto_eliminar', args=[self.producto.pk])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)

    def test_cajero_no_puede_eliminar_producto(self):
        self._login_user('cajero')
        url = reverse('productos:producto_eliminar', args=[self.producto.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_crea_categoria(self):
        self._login_user('admin')
        url = reverse('productos:categoria_crear')
        payload = {'nombre': 'Snacks', 'descripcion': 'Piqueos'}

        response = self.client.post(url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertTrue(Categoria.objects.filter(nombre='Snacks').exists())

    def test_crear_categoria_duplicada_devuelve_400(self):
        self._login_user('admin')
        url = reverse('productos:categoria_crear')
        payload = {'nombre': self.categoria.nombre}

        response = self.client.post(url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_admin_actualiza_categoria(self):
        self._login_user('admin')
        categoria = Categoria.objects.create(nombre='Snacks')
        url = reverse('productos:categoria_editar', args=[categoria.pk])
        payload = {'nombre': 'Snacks Premium', 'descripcion': 'Mejores piqueos'}

        response = self.client.post(url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, 'Snacks Premium')

    def test_admin_elimina_categoria_sin_productos(self):
        self._login_user('admin')
        categoria = Categoria.objects.create(nombre='Snacks')
        url = reverse('productos:categoria_eliminar', args=[categoria.pk])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        categoria.refresh_from_db()
        self.assertFalse(categoria.activo)

    def test_eliminar_categoria_con_productos_activos_devuelve_400(self):
        self._login_user('admin')
        url = reverse('productos:categoria_eliminar', args=[self.categoria.pk])

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())


class ProductoServiceTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre='Bebidas', descripcion='Refrescos')
        self.otra_categoria = Categoria.objects.create(nombre='Abarrotes')

    def test_crear_crea_producto_con_campos_correctos(self):
        data = {
            'nombre': 'Gaseosa 600ml',
            'categoria': self.categoria.id,
            'precio_venta': '3.50',
            'costo': '2.00',
            'stock_actual': '20',
            'stock_minimo': '5',
            'unidad': 'unidad',
            'codigo_barra': '789123',
            'descripcion': 'Gaseosa de cola',
        }

        producto = ProductoService.crear(data)

        self.assertIsInstance(producto, Producto)
        self.assertEqual(producto.nombre, 'Gaseosa 600ml')
        self.assertEqual(producto.categoria, self.categoria)
        self.assertEqual(producto.precio_venta, Decimal('3.50'))
        self.assertEqual(producto.costo, Decimal('2.00'))
        self.assertEqual(producto.stock_actual, 20)
        self.assertEqual(producto.stock_minimo, 5)
        self.assertTrue(producto.activo)

    def test_crear_con_precio_venta_menor_a_costo_lanza_margen_invalido(self):
        data = {
            'nombre': 'Producto defectuoso',
            'categoria': self.categoria.id,
            'precio_venta': '1.50',
            'costo': '2.00',
        }

        with self.assertRaises(MargenInvalidoError):
            ProductoService.crear(data)

    def test_actualizar_actualiza_campos_correctamente(self):
        producto = ProductoService.crear({
            'nombre': 'Jugo',
            'categoria': self.categoria.id,
            'precio_venta': '4.00',
            'costo': '2.50',
        })

        ProductoService.actualizar(producto, {
            'nombre': 'Jugo Premium',
            'categoria': self.otra_categoria.id,
            'precio_venta': '5.00',
            'costo': '3.00',
            'stock_actual': '15',
            'stock_minimo': '3',
            'unidad': 'litro',
            'codigo_barra': '111',
            'descripcion': 'Jugo natural',
        })
        producto.refresh_from_db()

        self.assertEqual(producto.nombre, 'Jugo Premium')
        self.assertEqual(producto.categoria, self.otra_categoria)
        self.assertEqual(producto.precio_venta, Decimal('5.00'))
        self.assertEqual(producto.costo, Decimal('3.00'))
        self.assertEqual(producto.stock_actual, 15)
        self.assertEqual(producto.stock_minimo, 3)
        self.assertEqual(producto.unidad, 'litro')

    def test_actualizar_con_precio_venta_menor_a_costo_lanza_margen_invalido(self):
        producto = ProductoService.crear({
            'nombre': 'Jugo',
            'categoria': self.categoria.id,
            'precio_venta': '4.00',
            'costo': '2.50',
        })

        with self.assertRaises(MargenInvalidoError):
            ProductoService.actualizar(producto, {'precio_venta': '2.00'})

    def test_eliminar_desactiva_producto(self):
        producto = ProductoService.crear({
            'nombre': 'Yogurt',
            'categoria': self.categoria.id,
            'precio_venta': '3.00',
            'costo': '1.50',
        })

        ProductoService.eliminar(producto)
        producto.refresh_from_db()

        self.assertFalse(producto.activo)


class ProductosCacheTests(SimpleTestCase):
    """Tests del cache de búsqueda de productos (get/set/invalidate)."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_miss_retorna_none(self):
        self.assertIsNone(get_cached_productos('gaseosa', scope='venta'))

    def test_set_y_get_devuelve_lo_guardado(self):
        payload = {'results': [{'id': 1, 'nombre': 'Gaseosa'}]}
        set_cached_productos('gaseosa', payload, scope='venta')
        self.assertEqual(get_cached_productos('gaseosa', scope='venta'), payload)

    def test_key_normaliza_mayusculas_y_espacios(self):
        payload = {'results': []}
        set_cached_productos('  Gaseosa  ', payload, scope='venta')
        self.assertEqual(get_cached_productos('gaseosa', scope='venta'), payload)

    def test_scopes_no_colisionan(self):
        set_cached_productos('agua', {'origen': 'venta'}, scope='venta')
        set_cached_productos('agua', {'origen': 'api'}, scope='api')
        self.assertEqual(get_cached_productos('agua', scope='venta'), {'origen': 'venta'})
        self.assertEqual(get_cached_productos('agua', scope='api'), {'origen': 'api'})

    def test_invalidate_limpia_el_cache(self):
        set_cached_productos('gaseosa', {'results': []}, scope='venta')
        invalidate_productos_cache()
        self.assertIsNone(get_cached_productos('gaseosa', scope='venta'))


class CategoriaServiceTests(TestCase):
    def test_crear_crea_categoria_con_campos_correctos(self):
        categoria = CategoriaService.crear(nombre='Lácteos', descripcion='Quesos y leches')

        self.assertIsInstance(categoria, Categoria)
        self.assertEqual(categoria.nombre, 'Lácteos')
        self.assertEqual(categoria.descripcion, 'Quesos y leches')
        self.assertTrue(categoria.activo)

    def test_crear_con_nombre_duplicado_lanza_regla_negocio_violada(self):
        CategoriaService.crear(nombre='Lacteos')

        with self.assertRaises(ReglaNegocioViolada):
            CategoriaService.crear(nombre='lacteos')

    def test_actualizar_actualiza_campos(self):
        categoria = CategoriaService.crear(nombre='Lácteos')

        CategoriaService.actualizar(categoria, nombre='Lácteos Frescos', descripcion='Frescos')
        categoria.refresh_from_db()

        self.assertEqual(categoria.nombre, 'Lácteos Frescos')
        self.assertEqual(categoria.descripcion, 'Frescos')

    def test_actualizar_con_nombre_duplicado_excluyendose_lanza_regla_negocio_violada(self):
        CategoriaService.crear(nombre='Lacteos')
        otra = CategoriaService.crear(nombre='Carnes')

        with self.assertRaises(ReglaNegocioViolada):
            CategoriaService.actualizar(otra, nombre='lacteos', descripcion='')

    def test_eliminar_con_productos_activos_lanza_regla_negocio_violada(self):
        categoria = CategoriaService.crear(nombre='Lácteos')
        ProductoService.crear({
            'nombre': 'Leche',
            'categoria': categoria.id,
            'precio_venta': '4.00',
            'costo': '2.50',
        })

        with self.assertRaises(ReglaNegocioViolada):
            CategoriaService.eliminar(categoria)

        categoria.refresh_from_db()
        self.assertTrue(categoria.activo)

    def test_eliminar_sin_productos_activos_desactiva_categoria(self):
        categoria = CategoriaService.crear(nombre='Lácteos')

        CategoriaService.eliminar(categoria)
        categoria.refresh_from_db()

        self.assertFalse(categoria.activo)
