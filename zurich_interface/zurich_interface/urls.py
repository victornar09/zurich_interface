"""zurich_interface URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from db_query.views import mi_vista, consultar_campos, procesar_campos, login, procesar_consulta_predefinida


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login, name='login'),
    path('table-list/', mi_vista, name='mi_vista'),
    path('consultar-campos/', consultar_campos, name='consultar_campos'),
    path('procesar-campos/', procesar_campos, name='procesar_campos'),
    path('procesar_consulta_predefinida/', procesar_consulta_predefinida, name='procesar_consulta_predefinida'),
]
