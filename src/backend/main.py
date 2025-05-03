import base64
import io
from flask import Flask, request, jsonify, session, make_response, send_file
import xml.etree.ElementTree as ET
import os
from matplotlib import pyplot as plt
from werkzeug.utils import secure_filename
import re
import uuid
from xml.dom import minidom
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor


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

        return autorizaciones_manager.get_all_authorizations()

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

            # Agregar errores específicos por tipo
            errores_totales = auth_data.get("errores", {})
            auth_data["errores"] = {
                "nit_emisor": errores_totales.get("nit_emisor", 0),
                "nit_receptor": errores_totales.get("nit_receptor", 0),
                "iva": errores_totales.get("iva", 0),
                "total": errores_totales.get("total", 0),
                "referencia_duplicada": errores_totales.get("referencia_duplicada", 0),
            }

            # Agregar facturas con errores
            auth_data["facturas_con_errores"] = (
                errores_totales.get("nit_emisor", 0)
                + errores_totales.get("nit_receptor", 0)
                + errores_totales.get("iva", 0)
                + errores_totales.get("total", 0)
                + errores_totales.get("referencia_duplicada", 0)
            )

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

def agregar_encabezado_y_pie(c, titulo, pagina_actual):
    # Fondo pastel
    c.setFillColor(HexColor("#FFFAE6"))  # Color pastel (amarillo claro)
    c.rect(0, 0, 612, 792, fill=True, stroke=False)  # Tamaño carta (612x792 puntos)

    # Encabezado
    c.setFillColor(colors.black)  # Cambiar el color del texto a negro
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, titulo)

    # Pie de página
    c.setFont("Helvetica", 10)
    c.drawString(100, 20, f"Página {pagina_actual}")
    c.drawString(400, 20, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


def generar_pdf(output_file_path):
    try:
        # Leer el archivo de salida XML
        tree = ET.parse(output_file_path)
        root = tree.getroot()

        # Crear el archivo PDF
        pdf_path = os.path.join("output", "autorizaciones.pdf")
        c = canvas.Canvas(pdf_path, pagesize=letter)
        pagina_actual = 1



        # Encabezado y pie de página
        agregar_encabezado_y_pie(c, "Reporte de Autorizaciones", pagina_actual)

        # Título general
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.darkblue)  # Cambiar el color del título
        c.drawString(200, 770, "Reporte")  # Posición del título

        c.setFont("Helvetica", 12)
        c.setFillColor(colors.black)  # Cambiar el color
        y = 750  # Posición inicial en el eje Y

        # Recorrer las autorizaciones y escribirlas en el PDF
        for autorizacion in root.findall("AUTORIZACION"):
            fecha = autorizacion.find("FECHA").text
            facturas_recibidas = autorizacion.find("FACTURAS_RECIBIDAS").text
            errores = autorizacion.find("ERRORES")
            facturas_correctas = autorizacion.find("FACTURAS_CORRECTAS").text
            cantidad_emisores = autorizacion.find("CANTIDAD_EMISORES").text
            cantidad_receptores = autorizacion.find("CANTIDAD_RECEPTORES").text

            # Cambiar color y escribir datos
            c.setFillColor(colors.blue)
            c.drawString(100, y, f"Fecha: {fecha}")
            y -= 15
            c.setFillColor(colors.black)
            c.drawString(120, y, f"Facturas recibidas: {facturas_recibidas}")
            y -= 15
            c.drawString(120, y, f"Facturas correctas: {facturas_correctas}")
            y -= 15
            c.drawString(120, y, f"Cantidad de emisores: {cantidad_emisores}")
            y -= 15
            c.drawString(120, y, f"Cantidad de receptores: {cantidad_receptores}")
            y -= 15

            # Escribir los errores
            c.drawString(120, y, "Errores:")
            y -= 15
            for error in errores:
                c.drawString(140, y, f"{error.tag}: {error.text}")
                y -= 15

            # Espacio entre autorizaciones
            y -= 20
            if y < 50:  # Salto de página si no hay espacio suficiente
                c.showPage()
                pagina_actual += 1
                agregar_encabezado_y_pie(c, "Reporte de Autorizaciones", pagina_actual)
                y = 750

        c.save()
        print(f"PDF generado correctamente en: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"Error al generar el PDF: {e}")
        return None



@app.route("/")
def hola():
    return "<h1>Hola, mundo! Este es el backend, anda al frontend</h1>"


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
    

@app.route('/generar_pdf', methods=['GET'])
def generar_pdf_endpoint():
    try:
        # Ruta del archivo XML de salida
        output_file_path = os.path.join("output", "autorizaciones.xml")

        # Generar el PDF
        pdf_path = generar_pdf(output_file_path)
        if pdf_path:
            return send_file(pdf_path, as_attachment=True)
        else:
            return jsonify({'error': 'Error al generar el PDF'}), 500
    except Exception as e:
        print(f"Error al generar el PDF: {e}")
        return jsonify({'error': str(e)}), 500
    


@app.route('/resumenIva', methods=['POST'])
def resumen_iva():
    print("Entrando a resumen_iva")
    
    try:
        # Obtener fecha de la consulta
        fecha = request.args.get('fecha')
        print("fecha: ", fecha)
        if not fecha:
            return jsonify({
                'success': False,
                'message': 'Debe especificar una fecha'
            }), 400

        try:
            fecha = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d/%m/%Y')  # Cambiar formato si es necesario
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido'
            }), 400
        
        print(f"Datos almacenados: {autorizaciones_manager.get_all_authorizations()}")


        # Obtener el resumen
        iva_summary = autorizaciones_manager.get_iva_by_date_and_nit(fecha)
        
        if not iva_summary:
            return jsonify({
                'success': False,
                'message': f'No hay datos para la fecha {fecha}'
            }), 404
        
        # Preparar los datos para la gráfica
        nits = list(iva_summary.keys())
        iva_emitido = [iva_summary[nit]['emitido'] for nit in nits]
        iva_recibido = [iva_summary[nit]['recibido'] for nit in nits]
        
        # Crear la gráfica
        fig, ax = plt.subplots(figsize=(10, 6))
        width = 0.35
        x = range(len(nits))
        
        # Barras para IVA emitido
        bars1 = ax.bar([i - width/2 for i in x], iva_emitido, width, label='IVA Emitido')
        
        # Barras para IVA recibido
        bars2 = ax.bar([i + width/2 for i in x], iva_recibido, width, label='IVA Recibido')
        
        # Configuración adicional
        ax.set_title(f'Resumen de IVA por NIT para la fecha {fecha}')
        ax.set_xlabel('NIT')
        ax.set_ylabel('IVA')
        ax.set_xticks(x)
        ax.set_xticklabels(nits, rotation=45, ha='right')
        ax.legend()
        
        # Ajustar layout
        plt.tight_layout()
        
        # Guardar la gráfica en memoria
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Convertir la imagen a base64
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        # Cerrar la figura para liberar memoria
        plt.close(fig)
        
        return jsonify({
            'success': True,
            'data': iva_summary,
            'graph': img_str
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al generar resumen: {str(e)}'
        }), 500



if __name__ == '__main__':
    app.run(debug=True)
    

