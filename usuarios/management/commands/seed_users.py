from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea/actualiza usuarios iniciales para desarrollo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-password",
            default="123",
            help="Password para el usuario admin (default: 123).",
        )
        parser.add_argument(
            "--cajero-password",
            default="123",
            help="Password para el usuario cajero (default: 123).",
        )

    def handle(self, *args, **options):
        user_model = get_user_model()

        seeds = [
            {
                "username": "admin",
                "password": options["admin_password"],
                "email": "admin@local.com",
                "rol": "admin",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
            {
                "username": "cajero",
                "password": options["cajero_password"],
                "email": "cajero@local.com",
                "rol": "cajero",
                "is_staff": False,
                "is_superuser": False,
                "is_active": True,
            },
        ]

        for row in seeds:
            user, created = user_model.objects.get_or_create(
                username=row["username"],
                defaults={
                    "email": row["email"],
                    "rol": row["rol"],
                    "is_staff": row["is_staff"],
                    "is_superuser": row["is_superuser"],
                    "is_active": row["is_active"],
                },
            )

            user.email = row["email"]
            user.rol = row["rol"]
            user.is_staff = row["is_staff"]
            user.is_superuser = row["is_superuser"]
            user.is_active = True
            user.set_password(row["password"])
            user.save()

            action = "creado" if created else "actualizado"
            self.stdout.write(
                self.style.SUCCESS(f"Usuario {user.username} {action}.")
            )

        self.stdout.write(self.style.SUCCESS("Seed de usuarios completado."))
