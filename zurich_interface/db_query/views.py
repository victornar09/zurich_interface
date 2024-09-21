import pandas as pd
from django.shortcuts import render, redirect
from django.db import connections, OperationalError
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

# Vista de inicio de sesión
def login(request):
    if request.method == 'POST':
        host = request.POST['host']
        database = request.POST['database']
        user = request.POST['user']
        password = request.POST['password']
        port = request.POST.get('port', '1433')  # Usar 1433 por defecto si no se proporciona

        try:
            connections['default'].close()  # Cerrar la conexión actual si hay alguna
            connections['default'].settings_dict.update({
                'ENGINE': 'sql_server.pyodbc',
                'HOST': host,
                'NAME': database,
                'USER': user,
                'PASSWORD': password,
                'PORT': port,
                'OPTIONS': {
                    'driver': 'ODBC Driver 17 for SQL Server',
                    'disable_migrations': True,
                },
            })
            connections['default'].connect()  # Conectar a la nueva base de datos
            logger.info("Conexión exitosa a la base de datos.")
            return redirect('mi_vista')  # Redirigir a la vista de tablas
        except OperationalError:
            return render(request, 'db_query/login.html', {'error': 'Error en la conexión a la base de datos.'})

    return render(request, 'db_query/login.html')

# Vista para listar tablas
def mi_vista(request):
    try:
        # Intenta conectar antes de verificar si es usable
        connections['default'].connect()
    except OperationalError:
        return redirect('login')  # Redirigir a login si no hay conexión

    with connections['default'].cursor() as cursor:
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = 'DM_ESTRAYFINA';")
        resultados = cursor.fetchall()

    tablas = [resultado[0] for resultado in resultados]
    return render(request, 'db_query/homeQuery.html', {'tablas': tablas})

# Vista para consultar campos
def consultar_campos(request):
    campos = []
    tabla_seleccionada = None

    if request.method == 'POST' and 'tabla' in request.POST:
        tabla_seleccionada = request.POST.get('tabla')

        with connections['default'].cursor() as cursor:
            cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tabla_seleccionada}'")
            campos = [row[0] for row in cursor.fetchall()]

    tablas = obtener_tablas()
    return render(request, 'db_query/homeQuery.html', {'tablas': tablas, 'campos': campos, 'tabla': tabla_seleccionada})

# Función para obtener tablas
def obtener_tablas():
    with connections['default'].cursor() as cursor:
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = 'DM_ESTRAYFINA';")
        resultados = cursor.fetchall()

    return [resultado[0] for resultado in resultados]

# Procesar campos seleccionados
def procesar_campos(request):
    if request.method == 'POST':
        campos_seleccionados = request.POST.getlist('campos')
        tabla = request.POST.get('tabla')
        filtros = []

        # Obtener filtros
        i = 1
        while True:
            filtro_campo = request.POST.get(f'filtroCampo-{i}')
            filtro_comparador = request.POST.get(f'filtroComparador-{i}')
            filtro_valor = request.POST.get(f'filtroValor-{i}')
            if not filtro_campo or not filtro_comparador or not filtro_valor:
                break

            logica = request.POST.get(f'filtroLogica-{i}', 'AND')  # Por defecto será AND
            filtros.append(f"{logica} [{filtro_campo}] {filtro_comparador} '{filtro_valor}'")
            i += 1

        # Construir la consulta SQL
        campos_con_corchetes = [f"[{campo}]" for campo in campos_seleccionados]
        campos = ', '.join(campos_con_corchetes)
        consulta = f"SELECT TOP 10 {campos} FROM DM_ESTRAYFINA.{tabla}"

        if filtros:
            consulta += " WHERE " + " ".join(filtros).replace(" AND", "AND").replace(" OR", "OR")

        print(consulta)

        try:
            with connections['default'].cursor() as cursor:
                cursor.execute(consulta)
                rows = cursor.fetchall()

            # Crear un DataFrame de pandas
            df = pd.DataFrame(rows, columns=campos_seleccionados)
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{tabla}_data.csv"'
            df.to_csv(path_or_buf=response, index=False)
            return response
        except Exception as e:
            logger.error(f"Error al procesar campos: {e}")
            return redirect('mi_vista')

    return redirect('mi_vista')
