from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils.timezone import now
import requests
import xml.etree.ElementTree as ET
import re

# Create your views here.
def home(request):
    if request.method == 'POST':
        if 'enviar' in request.POST:
            fileIndex = request.session.get('fileIndex')
            try:
                response = requests.post('http://127.0.0.1:5000/procesar_xml', json={'fileIndex': fileIndex})
                if response.status_code == 200:
                    data = response.json()
                    request.session['xml_dataSalida'] = data.get('salida_xml_content')
                    print("Archivo XML procesado correctamente")
                    return redirect('home')
                else:
                    print("Error al procesar el archivo XML en el backend Flask")
                    print(response.text)
                    return JsonResponse({'error': 'Error al procesar el archivo XML en Flask', 'details': response.text}, status=response.status_code)
            except requests.exceptions.RequestException as e:
                print(f"Error al conectar con el servidor Flask: {e}")
                return JsonResponse({'error': 'Error al conectar con el servidor Flask', 'details': str(e)}, status=500)
        elif 'reset' in request.POST:
            try:
                response = requests.post('http://127.0.0.1:5000/reset')
                if response.status_code == 200:
                    print("Reset realizado correctamente")
                    request.session['xml_dataEntrada'] = None
                    request.session['xml_dataSalida'] = None
                    return redirect('home')
                else:
                    print("Error al realizar el reset en el backend Flask")
                    print(response.text)
                    return JsonResponse({'error': 'Error al realizar el reset en Flask', 'details': response.text}, status=response.status_code)
            except requests.exceptions.RequestException as e:
                print(f"Error al conectar con el servidor Flask: {e}")
                return JsonResponse({'error': 'Error al conectar con el servidor Flask', 'details': str(e)}, status=500)

    context = {
        'timestamp': now().timestamp(),
        'xml_dataEntrada': request.session.get('xml_dataEntrada'),
        'xml_dataSalida': request.session.get('xml_dataSalida'),
    }
    return render(request, "home.html", context)

def cargarXml(request):

    if request.method == 'POST' and request.FILES.get('xml_file'):
        archivo_xml = request.FILES['xml_file']
        files = {'archivo_xml': archivo_xml.read()}
        response = requests.post('http://127.0.0.1:5000/cargar_xml', files=files)

        if response.status_code == 200:
            data = response.json()
            xml_dataEntrada = data.get('xml_content')
            fileIndex = data.get('fileIndex')
            request.session['xml_dataEntrada'] = xml_dataEntrada
            request.session['fileIndex'] = fileIndex
        else:
            request.session['xml_dataEntrada'] = 'Error al procesar el archivo XML en el backend Flask. CARGA'
        
        print("xml_dataEntrada: ", request.session['xml_dataEntrada'])
        return redirect('home')
    
    context = {
        'timestamp': now().timestamp(),
        'xml_dataEntrada': request.session.get('xml_dataEntrada'),
    }
    return render(request, "cargarXml.html", context)

def peticiones(request):
    xml_dataSalida = ""
    if request.method == "POST" and "consultar_datos" in request.POST:
        xml_dataSalida = request.session.get('xml_dataSalida', '')

    context = {
        'timestamp': now().timestamp(),
        'xml_data_salida': xml_dataSalida,
    }
    return render(request, "peticiones.html", context)

def ayuda(request):
    return render(request, "ayuda.html")


def resumenIva(request):
    resumen_iva_data = None
    graph_base64 = None
    error_message = None

    if request.method == "POST":
        fecha = request.POST.get("fecha")
        if not fecha:
            error_message = "Debe especificar una fecha."
        else:
            try:
                # Llamar al endpoint del backend Flask
                response = requests.post(f'http://127.0.0.1:5000/resumenIva?fecha={fecha}')
                if response.status_code == 200:
                    data = response.json()
                    resumen_iva_data = data.get("data")
                    graph_base64 = data.get("graph")
                else:
                    error_message = response.json().get("message", "Error al obtener el resumen de IVA.")
            except requests.exceptions.RequestException as e:
                error_message = f"Error al conectar con el servidor Flask: {str(e)}"

    context = {
        "resumen_iva_data": resumen_iva_data,
        "graph_base64": graph_base64,
        "error_message": error_message,
    }
    return render(request, "resumenIva.html", context)

