from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect


@require_http_methods(["GET"])
@csrf_protect
def login_view(request):
    """
    Renderiza la página de login.
    """
    return render(request, 'login.html')
