from flask import Flask, request, jsonify, session, make_response, send_file
import xml.etree.ElementTree as ET
import os
from werkzeug.utils import secure_filename
import re
import uuid
from xml.dom import minidom
from io import BytesIO
from datetime import datetime

from clases.factura import Factura
from clases.autorizaciones import AuthorizationManager
from clases.archivosXml import XmlHandler   
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'


xml_dataEntrada = None
xml_dataSalida = None


#* Declaracion de variables
baseDeDatosFalsa = {
    "data": []
}

filePaths = []
facturas = []

autorizaciones_manager = AuthorizationManager()

def quitarTildes(palabra):
    reemplazos = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("Á", "a"),
        ("É", "e"),
        ("Í", "i"),
        ("Ó", "o"),
        ("Ú", "u")
    )           
    
    for a, b in reemplazos:
        palabra = palabra.replace(a, b)
            
    return palabra


def procesarXml(filePath):
    print(f"Entrando a procesarXml con filePath: {filePath}")
    try:
        # Usar XmlHandler para parsear el archivo
        facturas = XmlHandler.parsearArchivo(filePath)

        facturasRecibidas = len(facturas)

        # Procesar cada factura
        for factura in facturas:
            # Obtener la fecha de la factura
            if not factura.fecha_obj:
                print(f"Factura sin fecha válida: {factura.to_dict()}")
                continue

            # Obtener o crear la autorización diaria para la fecha de la factura
            daily_auth = autorizaciones_manager.get_or_create_daily_authorization(factura.fecha_obj)

            # Incrementar el contador de facturas recibidas
            daily_auth.add_factura_recibida()

            # Validar la factura
            if daily_auth.check_referencia_duplicada(factura.referencia):
                # Si la referencia es duplicada, registrar el error
                continue

            # Validar los campos de la factura
            if not factura.validate_emisor_nit():
                daily_auth.add_error_nit_emisor()
            if not factura.validate_receptor_nit():
                daily_auth.add_error_nit_receptor()
            if not factura.validate_iva():
                daily_auth.add_error_iva()
            if not factura.validate_total():
                daily_auth.add_error_total()

            # Si la factura es válida, agregarla como correcta
            if factura.is_valid():
                daily_auth.add_factura_correcta(factura)

        # Obtener todas las autorizaciones procesadas
        authorizations = autorizaciones_manager.get_all_authorizations()

        print(f"Facturas recibidas: {facturasRecibidas}")
        print(f"Autorizaciones procesadas: {authorizations}")

        return authorizations

    except ET.ParseError as e:
        return {"error": f"Error al parsear el archivo XML: {str(e)}"}
    except Exception as e:
        print(f"Error al procesar el archivo XML: {e}")
        return {"error": "Error al procesar el archivo XML"}

def generarSalida(datosProcesados):
    try:
        # Obtener todas las autorizaciones
        authorizations = autorizaciones_manager.get_all_authorizations()
        print(f"Autorizaciones obtenidas: {authorizations}")

        # Agregar datos de errores y facturas con errores a cada autorización
        for date_string, auth_data in authorizations.items():
            print(f"Datos para {date_string}: {auth_data}")
            
            # Agregar errores totales y facturas con errores
            auth_data["errores"] = datosProcesados.get("erroresTotales", {})
            auth_data["facturas_con_errores"] = len(datosProcesados.get("facturasConErrores", []))

        # Escribir el archivo de salida usando XmlHandler
        output_file_path = os.path.join("output", "autorizaciones.xml")
        success = XmlHandler.writeOutput(output_file_path, authorizations)

        if success:
            print(f"Archivo de salida generado correctamente: {output_file_path}")
            return output_file_path
        else:
            print("Error al generar el archivo de salida")
            return None

    except Exception as e:
        print(f"Error al generar el XML de salida: {e}")
        return None

@app.route("/")
def hola():
    return "<h1>Hola, mundo!</h1>"


@app.route("/cargar_xml", methods=["POST"])
def cargar_xml():
    print("Entrando a cargar_xml")
    if 'archivo_xml' not in request.files:
        return jsonify({'error': 'No se envió ningun archivo XML'}), 400

    archivo_xml = request.files['archivo_xml']
    fileName = secure_filename(archivo_xml.filename)
    filePath = os.path.join('uploads', fileName)
    archivo_xml.save(filePath)
    
    #* genera un id para el filePath
    fileIndex = len(filePaths)
    filePaths.append(filePath)
    print(f"filePath en cargar_xml con indice: {fileIndex} y  filePath{filePath}")
    
    tree = ET.parse(filePath)
    root = tree.getroot()
    xml_content = ET.tostring(root, encoding='unicode')

    response = jsonify({'xml_content': xml_content, 'fileIndex': fileIndex})
    
    return response


@app.route('/reset', methods=['POST'])
def reset():
    #* Se llama a las listas
    global filePaths
    
    #* Se limpian las listas
    
    filePaths = []
    
    session.clear()

    return jsonify({'message': 'Se ha reiniciado la información'})


@app.route('/procesar_xml', methods=['POST', 'GET'])	
def procesar_xml():
    print("Entrando a procesar_xml")
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se enviaron datos en la solicitud'}), 400

        fileIndex = data.get('fileIndex')
        if fileIndex is None or fileIndex >= len(filePaths):
            return jsonify({'error': 'Indice invalido'}), 400

        filePath = filePaths[fileIndex]
        print(f"filePath en procesar_xml: {filePath}")

        if not filePath:
            return jsonify({'error': 'No se ha cargado ningun archivo XML XD'}), 400

        # Procesar el archivo de entrada
        datosProcesados = procesarXml(filePath)

        if "error" in datosProcesados:
            return jsonify(datosProcesados), 400

        # Generar el archivo de salida
        output_file_path = generarSalida(datosProcesados)
        if output_file_path is None:
            return jsonify({'error': 'Error al generar el XML de salida'}), 500
        
        with open(output_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()

        # Enviar el archivo de salida como respuesta
        return jsonify({'message': 'Archivo procesado correctamente', 'output_file': output_file_path,'salida_xml_content': xml_content})

    except Exception as e:
        print(f"Error al procesar el archivo XML: {e}")
        return jsonify({'error': str(e)}), 500
    

if __name__ == '__main__':
    app.run(debug=True)
    

