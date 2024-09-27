from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.urls import reverse

class CheckUrlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        login_url = reverse('login')  # Asegúrate de que 'login' es el nombre correcto de tu vista de login

        # Verificar si la URL está definida en urls.py
        try:
            resolve(request.path)
        except Resolver404:
            # Redirigir a la página de login si la URL no está definida
            return redirect(login_url)

        # Continuar con la respuesta si la URL es válida
        return self.get_response(request)