
from django.shortcuts import redirect
from django.urls import reverse
from django.http import Http404


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_urls = [reverse('login')]  # Asegúrate de que 'login' es el nombre correcto de tu vista de login

        # Permitir acceso a la URL de login
        if request.path in public_urls:
            return self.get_response(request)

        # Comprobar si el usuario está autenticado
        if not request.user.is_authenticated:
            return redirect('login')  # Redirigir a la vista de login

        return self.get_response(request)