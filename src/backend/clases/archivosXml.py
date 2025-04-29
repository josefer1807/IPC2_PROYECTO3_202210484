import os
import xml.etree.ElementTree as ET
from lxml import etree
from datetime import datetime
from decimal import Decimal

from clases.factura import Factura

class XmlHandler:
    
    @staticmethod
    def parsearArchivo(file_path):
        try:
            # Parsear el archivo XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Lista para almacenar los DTEs
            facturas = []
            
            # Recorrer todos los elementos DTE
            for dte_elem in root.findall(".//DTE"):
                try:
                    # Extraer la información del DTE
                    tiempo = dte_elem.find("TIEMPO").text.strip() if dte_elem.find("TIEMPO") is not None else ""
                    referencia = dte_elem.find("REFERENCIA").text.strip() if dte_elem.find("REFERENCIA") is not None else ""
                    nit_emisor = dte_elem.find("NIT_EMISOR").text.strip() if dte_elem.find("NIT_EMISOR") is not None else ""
                    nit_receptor = dte_elem.find("NIT_RECEPTOR").text.strip() if dte_elem.find("NIT_RECEPTOR") is not None else ""
                    valor = float(dte_elem.find("VALOR").text.strip()) if dte_elem.find("VALOR") is not None else 0.0
                    iva = float(dte_elem.find("IVA").text.strip()) if dte_elem.find("IVA") is not None else 0.0
                    total = float(dte_elem.find("TOTAL").text.strip()) if dte_elem.find("TOTAL") is not None else 0.0
                    
                    # Crear objeto Factura
                    factura = Factura(tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total)
                    facturas.append(factura)
                except Exception as e:
                    print(f"Error al procesar DTE: {e}")
                    continue
            
            print(f"Facturas procesadas: {len(facturas)}")
            return facturas
        except Exception as e:
            print(f"Error al leer archivo XML: {e}")
            return []

    @staticmethod
    def writeOutput(file_path, authorizations):
        try:
            # Crear el elemento raíz
            root = ET.Element("LISTAAUTORIZACIONES")
            
            # Agregar cada autorización
            for date_string, auth_data in authorizations.items():
                auth_elem = ET.SubElement(root, "AUTORIZACION")
                
                # Fecha
                fecha_elem = ET.SubElement(auth_elem, "FECHA")
                fecha_elem.text = date_string
                
                # Facturas recibidas
                facturas_recibidas_elem = ET.SubElement(auth_elem, "FACTURAS_RECIBIDAS")
                facturas_recibidas_elem.text = str(auth_data.get("facturas_recibidas", 0))
                
                # Errores
                errores_elem = ET.SubElement(auth_elem, "ERRORES")
                for key in ["nit_emisor", "nit_receptor", "iva", "total", "referencia_duplicada"]:
                    value = auth_data.get("errores", {}).get(key, 0)
                    error_elem = ET.SubElement(errores_elem, key.upper())
                    error_elem.text = str(value)
                
                # Facturas correctas
                facturas_correctas_elem = ET.SubElement(auth_elem, "FACTURAS_CORRECTAS")
                facturas_correctas_elem.text = str(auth_data.get("facturas_correctas", 0))
                
                # Cantidad de emisores
                cant_emisores_elem = ET.SubElement(auth_elem, "CANTIDAD_EMISORES")
                cant_emisores_elem.text = str(auth_data.get("cantidad_emisores", 0))
                
                # Cantidad de receptores
                cant_receptores_elem = ET.SubElement(auth_elem, "CANTIDAD_RECEPTORES")
                cant_receptores_elem.text = str(auth_data.get("cantidad_receptores", 0))
                
                # Listado de autorizaciones
                listado_elem = ET.SubElement(auth_elem, "LISTADO_AUTORIZACIONES")
                
                # Agregar cada aprobación
                for aprobacion in auth_data.get("aprobaciones", []):
                    nit_emisor, referencia, codigo = aprobacion
                    aprobacion_elem = ET.SubElement(listado_elem, "APROBACION")
                    
                    nit_emisor_elem = ET.SubElement(aprobacion_elem, "NIT_EMISOR")
                    nit_emisor_elem.set("ref", referencia)
                    nit_emisor_elem.text = nit_emisor
                    
                    codigo_elem = ET.SubElement(aprobacion_elem, "CODIGO_APROBACION")
                    codigo_elem.text = codigo
                
                # Total de aprobaciones
                total_aprob_elem = ET.SubElement(listado_elem, "TOTAL_APROBACIONES")
                total_aprob_elem.text = str(auth_data.get("total_aprobaciones", 0))
            
            # Crear un árbol XML y guardarlo
            tree = ET.ElementTree(root)
            
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Guardar el archivo con formato
            XmlHandler.indentarXml(tree, file_path)
            
            return True
        except Exception as e:
            print(f"Error al escribir archivo XML: {e}")
            return False


    @staticmethod
    def indentarXml(tree, file_path):
        """
        Guarda un archivo XML con formato legible
        """
        # Convertir a string
        rough_string = ET.tostring(tree.getroot(), 'utf-8')
        
        # Parsear con lxml para formatear
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(rough_string, parser)
        
        # Escribir a archivo con formato
        with open(file_path, 'wb') as f:
            f.write(etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True))
    
    @staticmethod
    def parse_xml_string(xml_string):
        """
        Parsea un string XML y retorna una lista de DTEs
        """
        try:
            # Parsear el string XML
            root = ET.fromstring(xml_string)
            
            # Lista para almacenar los DTEs
            facturas = []
            
            # Recorrer todos los elementos DTE
            for dte_elem in root.findall(".//DTE"):
                try:
                    # Extraer la información del DTE
                    tiempo = dte_elem.find("TIEMPO").text.strip() if dte_elem.find("TIEMPO") is not None else ""
                    referencia = dte_elem.find("REFERENCIA").text.strip() if dte_elem.find("REFERENCIA") is not None else ""
                    nit_emisor = dte_elem.find("NIT_EMISOR").text.strip() if dte_elem.find("NIT_EMISOR") is not None else ""
                    
                    # Verificar si NIT_RECEPTOR tiene etiquetas correctas
                    nit_receptor_elem = dte_elem.find("NIT_RECEPTOR")
                    if nit_receptor_elem is not None:
                        nit_receptor = nit_receptor_elem.text.strip() if nit_receptor_elem.text else ""
                    else:
                        # Buscar si hay algún elemento con el texto "NIT_RECEPTOR" pero mal cerrado
                        continue  # Ignorar este DTE si la etiqueta está mal formada
                    
                    valor_str = dte_elem.find("VALOR").text.strip() if dte_elem.find("VALOR") is not None else "0.0"
                    iva_str = dte_elem.find("IVA").text.strip() if dte_elem.find("IVA") is not None else "0.0"
                    total_str = dte_elem.find("TOTAL").text.strip() if dte_elem.find("TOTAL") is not None else "0.0"
                    
                    # Convertir valores a decimal
                    try:
                        valor = float(valor_str)
                        iva = float(iva_str)
                        total = float(total_str)
                    except ValueError:
                        # Si hay error en la conversión, usar valores por defecto
                        valor = 0.0
                        iva = 0.0
                        total = 0.0
                    
                    # Crear objeto DTE
                    factura = Factura(tiempo, referencia, nit_emisor, nit_receptor, valor, iva, total)
                    facturas.append(factura)
                except Exception as e:
                    # Ignorar DTEs con errores
                    print(f"Error al procesar DTE: {e}")
                    continue
            
            return facturas
        except Exception as e:
            print(f"Error al parsear string XML: {e}")
            return []