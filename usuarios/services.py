from django.contrib.auth import get_user_model

from core.exceptions import ReglaNegocioViolada

User = get_user_model()


class UsuarioService:
    """Servicio de dominio para operaciones de usuarios."""

    @staticmethod
    def _validar_rol(rol):
        valid_roles = {value for value, _ in User.ROL_CHOICES}
        if rol not in valid_roles:
            raise ReglaNegocioViolada(f"Rol inválido. Roles válidos: {', '.join(valid_roles)}")

    @classmethod
    def crear(cls, username, password, email=None, first_name="", last_name="", rol="cajero"):
        if not username.strip():
            raise ReglaNegocioViolada("El nombre de usuario es obligatorio.")
        if not password:
            raise ReglaNegocioViolada("La contraseña es obligatoria.")

        cls._validar_rol(rol)

        if User.objects.filter(username=username).exists():
            raise ReglaNegocioViolada("El nombre de usuario ya existe.")

        if email and User.objects.filter(email=email).exists():
            raise ReglaNegocioViolada("El email ya está en uso.")

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email or None,
            first_name=first_name,
            last_name=last_name,
        )
        user.rol = rol
        user.is_active = True
        user.save(update_fields=["rol", "is_active"])
        return user

    @classmethod
    def actualizar(cls, user, username, email=None, first_name="", last_name="", rol="cajero"):
        if not username.strip():
            raise ReglaNegocioViolada("El nombre de usuario es obligatorio.")

        cls._validar_rol(rol)

        if User.objects.filter(username=username).exclude(pk=user.pk).exists():
            raise ReglaNegocioViolada("El nombre de usuario ya existe.")

        if email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            raise ReglaNegocioViolada("El email ya está en uso.")

        user.username = username
        user.email = email or ""
        user.first_name = first_name
        user.last_name = last_name
        user.rol = rol
        user.save(update_fields=["username", "email", "first_name", "last_name", "rol"])
        return user

    @staticmethod
    def toggle_activo(user, target_user):
        if target_user.pk == user.pk:
            raise ReglaNegocioViolada("No podés desactivar tu propio usuario.")
        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=["is_active"])
        return target_user

    @staticmethod
    def reset_password(user, new_password):
        if not new_password:
            raise ReglaNegocioViolada("La contraseña es obligatoria.")
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return user
