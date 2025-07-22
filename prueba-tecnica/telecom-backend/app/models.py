import enum
from sqlalchemy import Column, Integer, String, DECIMAL, Date, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class EstadoFactura(str, enum.Enum):
    """Estados posibles de una factura."""
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"

class Usuario(Base):
    """
    Modelo de Usuario del sistema.
    Almacena credenciales y datos básicos del cliente.
    """
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), nullable=True)
    nombre_completo = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación con facturas
    facturas = relationship("Factura", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Usuario(id={self.id}, username='{self.username}')>"

class Factura(Base):
    """
    Modelo de Factura del sistema.
    Representa una factura de servicios de telecomunicaciones.
    """
    __tablename__ = "facturas"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    monto = Column(DECIMAL(10, 2), nullable=False)
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    estado = Column(Enum(EstadoFactura), nullable=False, default=EstadoFactura.PENDIENTE, index=True)
    descripcion = Column(String(500), nullable=True)
    numero_factura = Column(String(50), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relación con usuario
    usuario = relationship("Usuario", back_populates="facturas")

    def __repr__(self):
        return f"<Factura(id={self.id}, numero='{self.numero_factura}', monto={self.monto}, estado='{self.estado}')>"
