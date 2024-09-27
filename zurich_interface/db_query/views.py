import pandas as pd
from django.shortcuts import render, redirect
from django.db import connections, OperationalError
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User

import logging

logger = logging.getLogger(__name__)


# Modificar las consultas predefinidas para incluir nombres legibles
def obtener_consultas_predefinidas():
    queries = {}
    
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT id, nombre_consulta, query FROM DM_ESTRAYFINA.TEMP_QUERYS_ELIMINAR")
            rows = cursor.fetchall()

            for row in rows:
                id_query = row[0]  # id
                nombre_consulta = row[1]  # nombre_consulta
                query = row[2]  # query
                queries[nombre_consulta] = (nombre_consulta, query)
    except Exception as e:
        logger.error(f"Error al obtener consultas predefinidas: {e}")

    return queries
# Login view
def login(request):
    if request.method == 'POST':
        host = request.POST['host']
        database = request.POST['database']
        user = request.POST['user']
        password = request.POST['password']
        port = request.POST.get('port', '1433')

        try:
            connections['default'].close()
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

            connections['default'].connect()
            #request.session['db_connected'] = True
            # Here, you might want to create or authenticate a user session
            # For demo purposes, we will just redirect to the main view
            return redirect('mi_vista')
        except OperationalError:
            return render(request, 'db_query/login.html', {'error': 'Error en la conexión a la base de datos.'})

    return render(request, 'db_query/login.html')


# # Vista para listar tablas
def mi_vista(request):
    
    try:
        # Intenta conectar antes de verificar si es usable
        connections['default'].connect()
    except OperationalError:
        return redirect('login')  # Redirigir a login si no hay conexión

    # Obtener las tablas
    tablas = obtener_tablas()  # Asegúrate de que esta función está correctamente implementada

    predefined_queries = obtener_consultas_predefinidas()

    #print(predefined_queries)
    # Pasar las tablas y consultas predefinidas al renderizar la plantilla
    return render(request, 'db_query/homeQuery.html', {
        'tablas': tablas,
        'predefined_queries': predefined_queries
    })



def procesar_consulta_predefinida(request):
    try:
        # Intenta conectar antes de verificar si es usable
        connections['default'].connect()
    except OperationalError:
        return redirect('login')

    if request.method == 'POST':
        consulta = request.POST.get('consulta')
        param1 = request.POST.get('parametro1')
        param2 = request.POST.get('parametro2')

        print(consulta, param1, param2)

        if consulta and param1 and param2:  # Asegúrate de que se proporcionen todos los parámetros
            # Obtén las consultas predefinidas nuevamente en caso de que no esté disponible
            predefined_queries = obtener_consultas_predefinidas()
            
            if consulta in predefined_queries:  # Verifica si la consulta es válida
                query = predefined_queries[consulta][1]
                print(query)  # Obtén la consulta SQL
                try:
                    with connections['default'].cursor() as cursor:

                        cursor.execute(query, [param1, param2])
                        rows = cursor.fetchall()
                        descripcion = [col[0] for col in cursor.description]
                        print(type(descripcion), descripcion)

                    # Crea un DataFrame
                    df = pd.DataFrame(rows, columns=descripcion)
                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="{consulta}_data.csv"'
                    df.to_csv(path_or_buf=response, index=False)
                    return response
                except Exception as e:
                    logger.error(f"Error al procesar consulta predefinida: {e}")
                    return redirect('mi_vista')
            else:
                logger.error(f"Consulta no válida: {consulta}")
                return redirect('mi_vista')

    return redirect('mi_vista')

# Vista para consultar campos
def consultar_campos(request):

    try:
        # Intenta conectar antes de verificar si es usable
        connections['default'].connect()
    except OperationalError:
        return redirect('login')

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
            
            # Solo agrega la lógica si no es el primer filtro
            if filtros:
                filtros.append(f"{logica} [{filtro_campo}] {filtro_comparador} '{filtro_valor}'")
            else:
                filtros.append(f"[{filtro_campo}] {filtro_comparador} '{filtro_valor}'")  # Sin lógica para el primer filtro

            i += 1

        # Construir la consulta SQL
        campos_con_corchetes = [f"[{campo}]" for campo in campos_seleccionados]
        campos = ', '.join(campos_con_corchetes)
        consulta = f"SELECT TOP 10 {campos} FROM DM_ESTRAYFINA.{tabla}"

        if filtros:
            consulta += " WHERE " + " ".join(filtros)

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


