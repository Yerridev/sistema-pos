import json

from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect

from core.exceptions import ReglaNegocioViolada
from usuarios.services import UsuarioService

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
        users_qs = User.objects.all().order_by("-date_joined")
        paginator = Paginator(users_qs, 15)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        context = {
            "users": page_obj.object_list,
            "page_obj": page_obj,
            "roles": roles,
            "current_user_id": request.user.id,
            "page_title": "Usuarios",
            "active_nav": "usuarios:list",
        }
        return render(request, "dashboard/usuarios.html", context)


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioCreateView(View):
    def post(self, request):
        data = _parse_request_data(request)
        try:
            user = UsuarioService.crear(
                username=data.get("username", ""),
                password=data.get("password", ""),
                email=data.get("email"),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                rol=data.get("rol", "cajero"),
            )
        except ReglaNegocioViolada as exc:
            return JsonResponse({"error": str(exc)}, status=400)

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
        try:
            UsuarioService.actualizar(
                user=user,
                username=data.get("username", ""),
                email=data.get("email"),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                rol=data.get("rol", "cajero"),
            )
        except ReglaNegocioViolada as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({"success": True, "message": f'Usuario "{user.username}" actualizado correctamente.'})


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioStatusView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = _parse_request_data(request)
        is_active = data.get("is_active")
        if is_active is None:
            return JsonResponse({"error": "Estado inválido."}, status=400)

        try:
            UsuarioService.toggle_activo(
                user=request.user,
                target_user=user,
            )
        except ReglaNegocioViolada as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        estado = "activado" if user.is_active else "desactivado"
        return JsonResponse({"success": True, "message": f'Usuario "{user.username}" {estado}.'})


@method_decorator([login_required, admin_required], name="dispatch")
class UsuarioResetPasswordView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = _parse_request_data(request)
        password = (data.get("password") or "").strip()

        try:
            UsuarioService.reset_password(user=user, new_password=password)
        except ReglaNegocioViolada as exc:
            return JsonResponse({"error": str(exc)}, status=400)

        return JsonResponse({"success": True, "message": f'Contraseña actualizada para "{user.username}".'})
