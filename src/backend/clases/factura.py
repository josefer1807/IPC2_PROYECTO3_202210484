import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

class Factura:
    """
    Clase que representa un Documento Tributario Electrónico (DTE)
    """
    def __init__(self, tiempo="", referencia="", nit_emisor="", nit_receptor="", 
                valor=0.0, iva=0.0, total=0.0):
        self.tiempo = tiempo
        self.referencia = referencia
        self.nit_emisor = nit_emisor
        self.nit_receptor = nit_receptor
        self.valor = Decimal(str(valor))
        self.iva = Decimal(str(iva))
        self.total = Decimal(str(total))
        self.fecha = None
        self.hora = None
        self.extract_datetime()
        
        # Valores calculados para comparar
        self.calculated_iva = self.calculate_iva()
        self.calculated_total = self.calculate_total()
        
        # Validaciones
        self.is_emisor_valid = False
        self.is_receptor_valid = False
        self.is_iva_valid = False
        self.is_total_valid = False
        
        # Código de aprobación (se establecerá si es aprobado)
        self.approval_code = None
    
    def extract_datetime(self):
        """Extrae la fecha y hora del campo tiempo usando expresiones regulares"""
        try:
            # Regex para extraer la fecha y hora del formato: Guatemala, dd/mm/yyyy hh24:mi
            pattern = r'(?:.*,\s*)?(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{1,2})'
            match = re.search(pattern, self.tiempo)
            
            if match:
                self.fecha = match.group(1)
                self.hora = match.group(2)
                
                # Convertir a objeto datetime para facilitar el manejo
                fecha_obj = datetime.strptime(f"{self.fecha} {self.hora}", "%d/%m/%Y %H:%M")
                self.fecha_obj = fecha_obj
        except Exception as e:
            print(f"Error al extraer fecha y hora: {e}")
    
    def get_date_string(self):
        """Retorna la fecha en formato dd/mm/yyyy"""
        if self.fecha:
            return self.fecha
        return ""
    
    def get_date_for_approval(self):
        """Retorna la fecha en formato yyyymmdd para el código de aprobación"""
        if self.fecha_obj:
            return self.fecha_obj.strftime("%Y%m%d")
        return ""
    
    def calculate_iva(self):
        """Calcula el IVA del valor (valor * 0.12)"""
        iva = self.valor * Decimal('0.12')
        # Redondear a 2 decimales
        return iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_total(self):
        """Calcula el total (valor + iva)"""
        return self.valor + self.calculated_iva
    
    def validate_emisor_nit(self):
        """Valida el NIT del emisor"""
        self.is_emisor_valid = self.validate_nit(self.nit_emisor)
        return self.is_emisor_valid
    
    def validate_receptor_nit(self):
        """Valida el NIT del receptor"""
        self.is_receptor_valid = self.validate_nit(self.nit_receptor)
        return self.is_receptor_valid
    
    def validate_iva(self):
        """Valida que el IVA sea correcto"""
        self.is_iva_valid = (self.iva == self.calculated_iva)
        return self.is_iva_valid
    
    def validate_total(self):
        """Valida que el total sea correcto"""
        self.is_total_valid = (self.total == self.calculated_total)
        return self.is_total_valid
    
    def is_valid(self):
        """Retorna True si todas las validaciones son correctas"""
        return (self.validate_emisor_nit() and 
                self.validate_receptor_nit() and 
                self.validate_iva() and 
                self.validate_total())
    
    @staticmethod
    def validate_nit(nit):
        """
        Valida un NIT utilizando el algoritmo especificado:
        1. Multiplica cada carácter por su posición respectiva (de derecha a izquierda)
        2. Suma todos los resultados
        3. Obtiene el módulo 11 de la sumatoria
        4. A 11 le resta el resultado del punto 3
        5. Calcula el módulo 11 del resultado del punto 4
        """
        try:
            # Eliminar espacios en blanco
            nit = nit.strip()
            
            # Verificar que el NIT tenga al menos 2 caracteres (1 dígito + 1 verificador)
            if len(nit) < 2:
                return False
            
            # Separar el dígito verificador
            digits = nit[:-1]
            verificador = nit[-1].upper()  # Convertir a mayúscula para manejar 'K'
            
            # Verificar que todos los dígitos sean números
            if not digits.isdigit():
                return False
            
            # Aplicar el algoritmo de validación
            suma = 0
            for i, digit in enumerate(digits[::-1]):
                suma += int(digit) * (i + 2)  # +2 porque empezamos en posición 2
            
            modulo = suma % 11
            resultado = 11 - modulo
            final_modulo = resultado % 11
            
            # Verificar el resultado
            if final_modulo == 10:
                return verificador == 'K'
            else:
                return verificador == str(final_modulo)
        except Exception:
            return False
    
    def set_approval_code(self, correlative):
        """Establece el código de aprobación con el formato yyyymmdd########"""
        if self.fecha_obj:
            date_part = self.fecha_obj.strftime("%Y%m%d")
            print(f"Correlative antes de formatear: {correlative} (tipo: {type(correlative)})")
            correlative = int(correlative)

            # Formatear el correlativo con ceros a la izquierda
            correlative_part = f"{correlative:08d}"
            self.approval_code = f"{date_part}{correlative_part}"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario"""
        return {
            'tiempo': self.tiempo,
            'referencia': self.referencia,
            'nit_emisor': self.nit_emisor,
            'nit_receptor': self.nit_receptor,
            'valor': float(self.valor),
            'iva': float(self.iva),
            'total': float(self.total),
            'fecha': self.get_date_string(),
            'is_emisor_valid': self.is_emisor_valid,
            'is_receptor_valid': self.is_receptor_valid,
            'is_iva_valid': self.is_iva_valid,
            'is_total_valid': self.is_total_valid,
            'approval_code': self.approval_code
        }