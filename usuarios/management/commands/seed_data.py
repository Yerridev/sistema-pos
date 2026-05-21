from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from productos.models import Categoria, Producto


class Command(BaseCommand):
    help = "Carga datos iniciales realistas (usuarios, categorias y productos)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="123",
            help="Password base para usuarios iniciales (default: 123).",
        )

    def handle(self, *args, **options):
        password = options["password"]
        user_model = get_user_model()

        users = [
            {
                "username": "admin",
                "email": "admin@local.com",
                "first_name": "Administrador",
                "last_name": "POS",
                "rol": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "cajero",
                "email": "cajero@local.com",
                "first_name": "Caja",
                "last_name": "Principal",
                "rol": "cajero",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        for row in users:
            user, created = user_model.objects.get_or_create(
                username=row["username"],
                defaults={
                    "email": row["email"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "rol": row["rol"],
                    "is_staff": row["is_staff"],
                    "is_superuser": row["is_superuser"],
                    "is_active": True,
                },
            )
            user.email = row["email"]
            user.first_name = row["first_name"]
            user.last_name = row["last_name"]
            user.rol = row["rol"]
            user.is_staff = row["is_staff"]
            user.is_superuser = row["is_superuser"]
            user.is_active = True
            user.set_password(password)
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Usuario {'creado' if created else 'actualizado'}: {user.username}"
                )
            )

        categories = [
            ("Abarrotes", "Productos de consumo diario"),
            ("Bebidas", "Gaseosas, jugos y aguas"),
            ("Limpieza", "Productos de aseo del hogar"),
            ("Lácteos", "Leches, yogures y derivados"),
            ("Snacks", "Galletas, chips y dulces"),
            ("Cuidado Personal", "Higiene y cuidado diario"),
        ]

        category_map = {}
        for name, description in categories:
            category, created = Categoria.objects.get_or_create(
                nombre=name,
                defaults={"descripcion": description, "activo": True},
            )
            if not created:
                category.descripcion = description
                category.activo = True
                category.save(update_fields=["descripcion", "activo", "updated_at"])

            category_map[name] = category
            self.stdout.write(
                self.style.SUCCESS(
                    f"Categoria {'creada' if created else 'actualizada'}: {name}"
                )
            )

        products = [
            {
                "codigo_barra": "7750010001011",
                "nombre": "Arroz Superior 5kg",
                "categoria": "Abarrotes",
                "descripcion": "Arroz graneado premium",
                "precio_venta": Decimal("24.90"),
                "costo": Decimal("19.50"),
                "stock_actual": 35,
                "stock_minimo": 8,
                "unidad": "unidad",
            },
            {
                "codigo_barra": "7750010001028",
                "nombre": "Azúcar Rubia 1kg",
                "categoria": "Abarrotes",
                "descripcion": "Azúcar para uso diario",
                "precio_venta": Decimal("4.80"),
                "costo": Decimal("3.70"),
                "stock_actual": 60,
                "stock_minimo": 15,
                "unidad": "unidad",
            },
            {
                "codigo_barra": "7750010002018",
                "nombre": "Aceite Vegetal 1L",
                "categoria": "Abarrotes",
                "descripcion": "Aceite vegetal refinado",
                "precio_venta": Decimal("9.90"),
                "costo": Decimal("7.40"),
                "stock_actual": 40,
                "stock_minimo": 10,
                "unidad": "litro",
            },
            {
                "codigo_barra": "7750010003015",
                "nombre": "Gaseosa Cola 3L",
                "categoria": "Bebidas",
                "descripcion": "Bebida gaseosa familiar",
                "precio_venta": Decimal("11.50"),
                "costo": Decimal("8.90"),
                "stock_actual": 28,
                "stock_minimo": 8,
                "unidad": "unidad",
            },
            {
                "codigo_barra": "7750010003022",
                "nombre": "Agua Mineral 625ml",
                "categoria": "Bebidas",
                "descripcion": "Agua sin gas",
                "precio_venta": Decimal("2.20"),
                "costo": Decimal("1.30"),
                "stock_actual": 80,
                "stock_minimo": 20,
                "unidad": "unidad",
            },
            {
                "codigo_barra": "7750010004012",
                "nombre": "Detergente Polvo 800g",
                "categoria": "Limpieza",
                "descripcion": "Limpieza profunda",
                "precio_venta": Decimal("8.90"),
                "costo": Decimal("6.20"),
                "stock_actual": 26,
                "stock_minimo": 8,
                "unidad": "unidad",
            },
            {
                "codigo_barra": "7750010004029",
                "nombre": "Lejía 1L",
                "categoria": "Limpieza",
                "descripcion": "Desinfectante multiuso",
                "precio_venta": Decimal("3.50"),
                "costo": Decimal("2.20"),
                "stock_actual": 45,
                "stock_minimo": 12,
                "unidad": "litro",
            },
            {
                "codigo_barra": "7750010005019",
                "nombre": "Leche Evaporada 400g",
                "categoria": "Lácteos",
                "descripcion": "Leche evaporada entera",
                "precio_venta": Decimal("4.30"),
                "costo": Decimal("3.20"),
                "stock_actual": 70,
                "stock_minimo": 15,
                "unidad": "unidad",
            },
            {
                "codigo_barra": "7750010006016",
                "nombre": "Papas Fritas 150g",
                "categoria": "Snacks",
                "descripcion": "Snack crocante",
                "precio_venta": Decimal("3.80"),
                "costo": Decimal("2.40"),
                "stock_actual": 55,
                "stock_minimo": 12,
                "unidad": "unidad",
            },
            {
                "codigo_barra": "7750010007013",
                "nombre": "Shampoo 400ml",
                "categoria": "Cuidado Personal",
                "descripcion": "Cuidado diario del cabello",
                "precio_venta": Decimal("14.90"),
                "costo": Decimal("10.80"),
                "stock_actual": 18,
                "stock_minimo": 6,
                "unidad": "unidad",
            },
        ]

        for row in products:
            product, created = Producto.objects.get_or_create(
                codigo_barra=row["codigo_barra"],
                defaults={
                    "nombre": row["nombre"],
                    "categoria": category_map[row["categoria"]],
                    "descripcion": row["descripcion"],
                    "precio_venta": row["precio_venta"],
                    "costo": row["costo"],
                    "stock_actual": row["stock_actual"],
                    "stock_minimo": row["stock_minimo"],
                    "unidad": row["unidad"],
                    "activo": True,
                },
            )

            if not created:
                product.nombre = row["nombre"]
                product.categoria = category_map[row["categoria"]]
                product.descripcion = row["descripcion"]
                product.precio_venta = row["precio_venta"]
                product.costo = row["costo"]
                product.stock_actual = row["stock_actual"]
                product.stock_minimo = row["stock_minimo"]
                product.unidad = row["unidad"]
                product.activo = True
                product.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Producto {'creado' if created else 'actualizado'}: {product.nombre}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Seed de datos iniciales completado."))
