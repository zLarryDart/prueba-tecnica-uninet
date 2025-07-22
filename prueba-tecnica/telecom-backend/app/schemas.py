from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from .models import EstadoFactura

# Schemas para Factura
class FacturaBase(BaseModel):
    """Schema base para Factura."""
    monto: Decimal = Field(..., gt=0, description="Monto debe ser mayor a 0")
    fecha_emision: date = Field(..., description="Fecha de emisión de la factura")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción de la factura")
    numero_factura: Optional[str] = Field(None, max_length=50, description="Número de factura")

class FacturaCreate(FacturaBase):
    """Schema para crear una nueva factura."""
    usuario_id: int = Field(..., gt=0, description="ID del usuario propietario")
    
    @validator('fecha_vencimiento')
    def validate_fecha_vencimiento(cls, v, values):
        if v and 'fecha_emision' in values and v < values['fecha_emision']:
            raise ValueError('Fecha de vencimiento no puede ser anterior a fecha de emisión')
        return v

class FacturaCreateSimple(BaseModel):
    """Schema simple para crear facturas de prueba."""
    monto: float = Field(..., gt=0, description="Monto de la factura")
    descripcion: str = Field("Factura de servicios", description="Descripción de la factura")
    dias_vencimiento: Optional[int] = Field(30, description="Días hasta vencimiento")

class Factura(FacturaBase):
    """Schema completo de Factura para respuestas."""
    id: int
    usuario_id: int
    estado: EstadoFactura
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FacturaDetallada(Factura):
    """Schema extendido de Factura con información adicional para vista de detalles."""
    dias_para_vencimiento: Optional[int] = None
    puede_pagar: bool = False
    monto_formateado: str = ""
    
    class Config:
        from_attributes = True

class PagoResponse(BaseModel):
    """Schema para respuesta de pago exitoso."""
    success: bool
    message: str
    factura: Factura
    monto_pagado: str
    fecha_pago: Optional[datetime] = None

class EstadisticasUsuario(BaseModel):
    """Schema para estadísticas del usuario."""
    total_facturas: int
    facturas_pendientes: int
    facturas_pagadas: int
    monto_total_pendiente: str
    monto_total_pagado: str

class ResumenFacturas(BaseModel):
    """Schema para resumen completo de facturas separadas por estado."""
    facturas_pendientes: List[Factura]
    facturas_pagadas: List[Factura]
    estadisticas: EstadisticasUsuario

# Schemas para Usuario
class UsuarioBase(BaseModel):
    """Schema base para Usuario."""
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario")
    email: Optional[str] = Field(None, description="Email del usuario")
    nombre_completo: Optional[str] = Field(None, description="Nombre completo del usuario")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('Username debe contener solo letras y números')
        return v.lower()

class UsuarioCreate(UsuarioBase):
    """Schema para crear un nuevo usuario."""
    password: str = Field(..., min_length=6, description="Contraseña mínimo 6 caracteres")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password debe tener al menos 6 caracteres')
        return v

class Usuario(UsuarioBase):
    """Schema completo de Usuario para respuestas."""
    id: int
    created_at: Optional[datetime] = None
    facturas: List[Factura] = []
    
    class Config:
        from_attributes = True

# Schemas para respuestas
class FacturasPaginadas(BaseModel):
    """Schema para respuesta paginada de facturas."""
    facturas: List[Factura]
    total: int
    page: int = 1
    per_page: int = 10

class EstadisticasUsuario(BaseModel):
    """Schema para estadísticas del usuario."""
    total_facturas: int
    facturas_pendientes: int
    facturas_pagadas: int
    monto_total_pendiente: Decimal
    monto_total_pagado: Decimal

# Schema para autenticación
class Token(BaseModel):
    """Schema para respuesta de token JWT."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 horas en segundos

class TokenData(BaseModel):
    """Schema para datos del token."""
    username: Optional[str] = None

# Schema para mensajes de respuesta
class Message(BaseModel):
    """Schema para mensajes de respuesta simples."""
    message: str
    success: bool = True
