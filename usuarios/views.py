from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect


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