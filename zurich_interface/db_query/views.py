import pandas as pd
from django.shortcuts import render, redirect
from django.db import connections, OperationalError
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)


# Modificar las consultas predefinidas para incluir nombres legibles
PREDEFINED_QUERIES = {
    'Consulta 1': ('Consulta 1 - Descripción', 'SELECT * FROM DM_ESTRAYFINA.Tabla1 WHERE campo1 = %s AND campo2 = %s'),
    'Consulta 2': ('Consulta 2 - Descripción', 'SELECT * FROM DM_ESTRAYFINA.Tabla2 WHERE campoA = %s AND campoB = %s'),
    'Consulta 3': ('Consulta 3 - Descripción', 'SELECT * FROM DM_ESTRAYFINA.Tabla3 WHERE campoX = %s AND campoY = %s'),
    'Consulta 4': ('Consulta 4 - Descripción', 'SELECT * FROM DM_ESTRAYFINA.Tabla4 WHERE campoM = %s AND campoN = %s'),
    'Consulta 5': ('Consulta 5 - Descripción', 'SELECT * FROM DM_ESTRAYFINA.Tabla5 WHERE campoAlpha = %s AND campoBeta = %s'),
    'Consulta 6': ('Consulta 6 - Descripción', 'SELECT * FROM DM_ESTRAYFINA.Tabla6 WHERE campoI = %s AND campoII = %s'),
}



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

    # Obtener las tablas
    tablas = obtener_tablas()  # Asegúrate de que esta función está correctamente implementada

    # Pasar las tablas y consultas predefinidas al renderizar la plantilla
    return render(request, 'db_query/homeQuery.html', {
        'tablas': tablas,
        'predefined_queries': PREDEFINED_QUERIES
    })



def procesar_consulta_predefinida(request):
    if request.method == 'POST':
        consulta = request.POST.get('consulta')
        param1 = request.POST.get('parametro1')
        param2 = request.POST.get('parametro2')

        if consulta and param1 and param2:  # Ensure all parameters are provided
            query = PREDEFINED_QUERIES[consulta][1]  # Get the SQL query
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute(query, [param1, param2])
                    rows = cursor.fetchall()

                # Create a DataFrame
                df = pd.DataFrame(rows, columns=[col[0] for col in cursor.description])
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{consulta}_data.csv"'
                df.to_csv(path_or_buf=response, index=False)
                return response
            except Exception as e:
                logger.error(f"Error al procesar consulta predefinida: {e}")
                return redirect('mi_vista')

    return redirect('mi_vista')

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


