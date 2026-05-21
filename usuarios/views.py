import json

from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect

User = get_user_model()


def _is_admin(user):
    return bool(user and user.is_authenticated and getattr(user, "rol", None) == "admin")


admin_required = user_passes_test(_is_admin)


def _parse_request_data(request):
    if request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            pass
    return request.POST.dict()


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    Renderiza y procesa el formulario de login.
    POST: autentica usuario y crea sesión
    GET: muestra página de login
    """
    if request.user.is_authenticated:
        return redirect('productos:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                next_url = request.GET.get('next', 'productos:dashboard')
                return redirect(next_url)
            else:
                return render(request, 'login.html', {
                    'error': 'Tu cuenta está desactivada. Contacta al administrador.'
                })
        else:
            return render(request, 'login.html', {
                'error': 'Usuario o contraseña incorrectos.'
            })

    return render(request, 'login.html')


@require_http_methods(["GET", "POST"])
@csrf_protect
def logout_view(request):
    """
    Cierra la sesión y redirige al login.
    POST es el método preferido (protegido con CSRF).
    GET se acepta por compatibilidad con el enlace del sidebar.
    """
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')


@require_http_methods(["GET"])
def dashboard_view(request):
    """
    Renderiza el panel principal posterior al login.
    """
    return render(request, 'dashboard.html')


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioListView(View):
    def get(self, request):
        roles = getattr(User, "ROL_CHOICES", [])
        users = User.objects.all().order_by("-date_joined")
        context = {
            "users": users,
            "roles": roles,
            "current_user_id": request.user.id,
        }
        return render(request, "dashboard/usuarios.html", context)


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioCreateView(View):
    def post(self, request):
        data = _parse_request_data(request)
        errors = {}

        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        email = (data.get("email") or "").strip()
        first_name = (data.get("first_name") or "").strip()
        last_name = (data.get("last_name") or "").strip()
        rol = (data.get("rol") or "").strip()

        roles = getattr(User, "ROL_CHOICES", [])
        valid_roles = {value for value, _ in roles}

        if not username:
            errors["username"] = "El usuario es obligatorio."
        if not password:
            errors["password"] = "La contraseña es obligatoria."
        if not rol:
            errors["rol"] = "El rol es obligatorio."
        elif valid_roles and rol not in valid_roles:
            errors["rol"] = "Rol inválido."

        if username and User.objects.filter(username=username).exists():
            errors["username"] = "El usuario ya existe."
        if email and User.objects.filter(email=email).exclude(username=username).exists():
            errors["email"] = "El email ya está en uso."

        if errors:
            return JsonResponse({"errors": errors}, status=400)

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

        return JsonResponse({"success": True, "message": f'Usuario "{user.username}" creado correctamente.'}, status=201)


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioDetailView(View):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return JsonResponse({
            "id": user.id,
            "username": user.username,
            "email": user.email or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "rol": getattr(user, "rol", ""),
            "is_active": user.is_active,
        })


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioUpdateView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = _parse_request_data(request)
        errors = {}

        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        first_name = (data.get("first_name") or "").strip()
        last_name = (data.get("last_name") or "").strip()
        rol = (data.get("rol") or "").strip()

        roles = getattr(User, "ROL_CHOICES", [])
        valid_roles = {value for value, _ in roles}

        if not username:
            errors["username"] = "El usuario es obligatorio."
        if not rol:
            errors["rol"] = "El rol es obligatorio."
        elif valid_roles and rol not in valid_roles:
            errors["rol"] = "Rol inválido."

        if username and User.objects.filter(username=username).exclude(pk=user.pk).exists():
            errors["username"] = "El usuario ya existe."
        if email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            errors["email"] = "El email ya está en uso."

        if errors:
            return JsonResponse({"errors": errors}, status=400)

        user.username = username
        user.email = email or ""
        user.first_name = first_name
        user.last_name = last_name
        user.rol = rol
        user.save(update_fields=["username", "email", "first_name", "last_name", "rol"])

        return JsonResponse({"success": True, "message": f'Usuario "{user.username}" actualizado correctamente.'})


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioStatusView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.pk == request.user.pk:
            return JsonResponse({"error": "No podés desactivar tu propio usuario."}, status=400)

        data = _parse_request_data(request)
        is_active = data.get("is_active")
        if is_active is None:
            return JsonResponse({"error": "Estado inválido."}, status=400)

        user.is_active = is_active.lower() == "true"
        user.save(update_fields=["is_active"])
        estado = "activado" if user.is_active else "desactivado"
        return JsonResponse({"success": True, "message": f'Usuario "{user.username}" {estado}.'})


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioResetPasswordView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = _parse_request_data(request)
        password = (data.get("password") or "").strip()

        if not password:
            return JsonResponse({"errors": {"password": "La contraseña es obligatoria."}}, status=400)

        user.set_password(password)
        user.save(update_fields=["password"])
        return JsonResponse({"success": True, "message": f'Contraseña actualizada para "{user.username}".'})
