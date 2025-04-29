from datetime import datetime
from collections import defaultdict

class DailyAuthorization:
    """
    Clase que mantiene el control de las autorizaciones por día
    """
    def __init__(self, date):
        self.date = date
        self.date_string = date.strftime("%d/%m/%Y")
        self.facturas_recibidas = 0
        self.errores_nit_emisor = 0
        self.errores_nit_receptor = 0
        self.errores_iva = 0
        self.errores_total = 0
        self.errores_referencia_duplicada = 0
        self.facturas_correctas = 0
        self.emisores = set()
        self.receptores = set()
        self.aprobaciones = []  # Lista de tuplas (nit_emisor, referencia, codigo_aprobacion)
        self.referencias_procesadas = set()  # Para controlar referencias duplicadas
        
        # Para reportes
        self.iva_por_emisor = defaultdict(float)  # NIT emisor -> suma de IVA
        self.iva_por_receptor = defaultdict(float)  # NIT receptor -> suma de IVA
        self.valor_por_emisor = defaultdict(float)  # NIT emisor -> suma de valor
        self.valor_por_receptor = defaultdict(float)  # NIT receptor -> suma de valor
        self.total_por_emisor = defaultdict(float)  # NIT emisor -> suma de total
        self.total_por_receptor = defaultdict(float)  # NIT receptor -> suma de total
        
        # Contador para el correlativo diario
        self.current_correlative = 1
    
    def reset_daily_counter(self):
        """Reinicia el contador del correlativo diario"""
        self.current_correlative = 1
    
    def get_next_correlative(self):
        """Obtiene el siguiente correlativo y lo incrementa"""
        correlative = self.current_correlative
        self.current_correlative += 1
        return correlative
    
    def add_factura_recibida(self):
        """Incrementa el contador de facturas recibidas"""
        self.facturas_recibidas += 1
    
    def add_error_nit_emisor(self):
        """Incrementa el contador de errores de NIT emisor"""
        self.errores_nit_emisor += 1
    
    def add_error_nit_receptor(self):
        """Incrementa el contador de errores de NIT receptor"""
        self.errores_nit_receptor += 1
    
    def add_error_iva(self):
        """Incrementa el contador de errores de IVA"""
        self.errores_iva += 1
    
    def add_error_total(self):
        """Incrementa el contador de errores de total"""
        self.errores_total += 1
    
    def check_referencia_duplicada(self, referencia):
        """
        Verifica si una referencia ya fue procesada
        Retorna True si es duplicada, False si no
        """
        if referencia in self.referencias_procesadas:
            self.errores_referencia_duplicada += 1
            return True
        
        self.referencias_procesadas.add(referencia)
        return False
    
    def add_factura_correcta(self, dte):
        """
        Agrega una factura correcta y actualiza emisores, receptores y aprobaciones
        """
        self.facturas_correctas += 1
        self.emisores.add(dte.nit_emisor)
        self.receptores.add(dte.nit_receptor)
        
        # Obtener el siguiente correlativo
        correlative = self.get_next_correlative()
        
        # Establecer el código de aprobación en el DTE
        dte.set_approval_code(correlative)
        
        # Agregar la aprobación a la lista
        self.aprobaciones.append((dte.nit_emisor, dte.referencia, dte.approval_code))
        
        # Actualizar datos para reportes
        self.iva_por_emisor[dte.nit_emisor] += float(dte.iva)
        self.iva_por_receptor[dte.nit_receptor] += float(dte.iva)
        self.valor_por_emisor[dte.nit_emisor] += float(dte.valor)
        self.valor_por_receptor[dte.nit_receptor] += float(dte.valor)
        self.total_por_emisor[dte.nit_emisor] += float(dte.total)
        self.total_por_receptor[dte.nit_receptor] += float(dte.total)
    
    def get_cantidad_emisores(self):
        """Retorna la cantidad de emisores distintos"""
        return len(self.emisores)
    
    def get_cantidad_receptores(self):
        """Retorna la cantidad de receptores distintos"""
        return len(self.receptores)
    
    def get_total_aprobaciones(self):
        """Retorna la cantidad total de aprobaciones"""
        return len(self.aprobaciones)
    
    def to_dict(self):
        """Convierte el objeto a un diccionario"""
        return {
            'fecha': self.date_string,
            'facturas_recibidas': self.facturas_recibidas,
            'errores': {
                'nit_emisor': self.errores_nit_emisor,
                'nit_receptor': self.errores_nit_receptor,
                'iva': self.errores_iva,
                'total': self.errores_total,
                'referencia_duplicada': self.errores_referencia_duplicada
            },
            'facturas_correctas': self.facturas_correctas,
            'cantidad_emisores': self.get_cantidad_emisores(),
            'cantidad_receptores': self.get_cantidad_receptores(),
            'aprobaciones': self.aprobaciones,
            'total_aprobaciones': self.get_total_aprobaciones()
        }


class AuthorizationManager:
    """
    Clase que gestiona todas las autorizaciones
    """
    def __init__(self):
        self.authorizations = {}  # fecha (string DD/MM/YYYY) -> DailyAuthorization
    
    def get_or_create_daily_authorization(self, date):
        """
        Obtiene la autorización diaria para una fecha dada
        Si no existe, la crea
        """
        date_string = date.strftime("%d/%m/%Y")
        
        if date_string not in self.authorizations:
            self.authorizations[date_string] = DailyAuthorization(date)
        
        return self.authorizations[date_string]
    
    def process_dte(self, dte):
        """
        Procesa un DTE y actualiza las estadísticas correspondientes
        Retorna el código de aprobación si es válido, None si no
        """
        # Extraer la fecha del DTE
        if not dte.fecha_obj:
            # No se pudo extraer la fecha del DTE
            return None
        
        # Obtener la autorización diaria para la fecha del DTE
        daily_auth = self.get_or_create_daily_authorization(dte.fecha_obj)
        
        # Incrementar contador de facturas recibidas
        daily_auth.add_factura_recibida()
        
        # Verificar si la referencia ya fue procesada
        if daily_auth.check_referencia_duplicada(dte.referencia):
            return None
        
        # Validar el DTE
        valid = True
        
        if not dte.validate_emisor_nit():
            daily_auth.add_error_nit_emisor()
            valid = False
        
        if not dte.validate_receptor_nit():
            daily_auth.add_error_nit_receptor()
            valid = False
        
        if not dte.validate_iva():
            daily_auth.add_error_iva()
            valid = False
        
        if not dte.validate_total():
            daily_auth.add_error_total()
            valid = False
        
        # Si el DTE es válido, agregarlo a las facturas correctas
        if valid:
            daily_auth.add_factura_correcta(dte)
            return dte.approval_code
        
        return None
    
    def get_all_authorizations(self):
        """Retorna un diccionario con todas las autorizaciones"""
        return {date: auth.to_dict() for date, auth in self.authorizations.items()}
    
    def get_authorization_by_date(self, date_string):
        """Retorna la autorización para una fecha dada"""
        if date_string in self.authorizations:
            return self.authorizations[date_string].to_dict()
        return None
    
    def get_iva_by_date_and_nit(self, date_string):
        """
        Retorna un diccionario con el IVA emitido y recibido por NIT para una fecha
        {
            'nit': {
                'emitido': valor,
                'recibido': valor
            }
        }
        """
        if date_string not in self.authorizations:
            return {}
        
        daily_auth = self.authorizations[date_string]
        result = {}
        
        # Agregar todos los NITs (emisores y receptores)
        all_nits = set(daily_auth.emisores) | set(daily_auth.receptores)
        
        for nit in all_nits:
            result[nit] = {
                'emitido': daily_auth.iva_por_emisor.get(nit, 0),
                'recibido': daily_auth.iva_por_receptor.get(nit, 0)
            }
        
        return result
    
    def get_summary_by_date_range(self, start_date, end_date, include_iva=True):
        """
        Retorna un resumen por rango de fechas
        {
            'fecha': valor
        }
        """
        result = {}
        
        # Convertir fechas a objetos datetime para comparar
        start_date_obj = datetime.strptime(start_date, "%d/%m/%Y")
        end_date_obj = datetime.strptime(end_date, "%d/%m/%Y")
        
        for date_string, auth in self.authorizations.items():
            date_obj = datetime.strptime(date_string, "%d/%m/%Y")
            
            # Verificar si la fecha está en el rango
            if start_date_obj <= date_obj <= end_date_obj:
                if include_iva:
                    # Sumar todos los totales para la fecha
                    total_suma = sum(auth.total_por_emisor.values())
                else:
                    # Sumar todos los valores (sin IVA) para la fecha
                    total_suma = sum(auth.valor_por_emisor.values())
                
                result[date_string] = total_suma
        
        return result
    
    def reset(self):
        """Reinicia todas las autorizaciones"""
        self.authorizations = {}