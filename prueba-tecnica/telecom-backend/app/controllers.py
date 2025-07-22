"""
Controladores para la API de Telecomunicaciones.
Implementa el patrón MVC separando la lógica de negocio de los endpoints.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from . import models, schemas, crud
from .deps import get_password_hash

class AuthController:
    """Controlador para autenticación y autorización."""
    
    @staticmethod
    def register_user(user_data: schemas.UsuarioCreate, db: Session) -> models.Usuario:
        """
        Registra un nuevo usuario en el sistema.
        Valida que el username no exista y cifra la contraseña.
        """
        # Verificar si el usuario ya existe
        existing_user = crud.get_user(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El username ya existe"
            )
        
        # Crear el usuario
        return crud.create_user(db, user_data)
    
    @staticmethod
    def authenticate_user(username: str, password: str, db: Session) -> Optional[models.Usuario]:
        """
        Autentica un usuario con username y password.
        Retorna el usuario si las credenciales son válidas.
        """
        print(f"Authenticating user: {username}")  # Debug
        user = crud.get_user(db, username)
        if not user:
            print(f"User not found: {username}")  # Debug
            return None
        
        print(f"User found: {user.username}, checking password...")  # Debug
        password_valid = crud.verify_pw(password, user.password_hash)
        print(f"Password verification result: {password_valid}")  # Debug
        
        if not password_valid:
            print(f"Password verification failed for user: {username}")  # Debug
            return None
        
        print(f"Authentication successful for user: {username}")  # Debug
        return user

class FacturaController:
    """Controlador para operaciones de facturas."""
    
    @staticmethod
    def get_user_facturas(user_id: int, db: Session) -> List[models.Factura]:
        """
        Obtiene todas las facturas de un usuario.
        Incluye validación de existencia del usuario.
        """
        # Verificar que el usuario existe
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return crud.list_facturas(db, user_id)
    
    @staticmethod
    def get_factura_by_id(factura_id: int, user_id: int, db: Session) -> models.Factura:
        """
        Obtiene una factura específica verificando que pertenezca al usuario.
        """
        factura = crud.get_factura_by_id(db, factura_id)
        
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        if factura.usuario_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a esta factura"
            )
        
        return factura
    
    @staticmethod
    def process_payment(factura_id: int, user_id: int, db: Session) -> models.Factura:
        """
        Procesa el pago de una factura.
        Incluye validaciones de negocio completas.
        """
        # Obtener la factura con validaciones
        factura = FacturaController.get_factura_by_id(factura_id, user_id, db)
        
        # Validar que la factura esté pendiente
        if factura.estado != models.EstadoFactura.PENDIENTE:
            if factura.estado == models.EstadoFactura.PAGADO:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La factura ya está pagada"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se puede pagar una factura en estado {factura.estado.value}"
                )
        
        # Validar fecha de vencimiento (opcional)
        if factura.fecha_vencimiento and factura.fecha_vencimiento < date.today():
            # Podrías permitir el pago pero con un recargo, o rechazarlo
            pass  # Por ahora permitimos el pago de facturas vencidas
        
        # Procesar el pago
        try:
            factura_pagada = crud.pay_factura(db, factura_id)
            if not factura_pagada:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al procesar el pago"
                )
            return factura_pagada
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al procesar el pago"
            )
    
    @staticmethod
    def get_user_statistics(user_id: int, db: Session) -> schemas.EstadisticasUsuario:
        """
        Calcula estadísticas de facturas para un usuario.
        """
        facturas = crud.list_facturas(db, user_id)
        
        total_facturas = len(facturas)
        facturas_pendientes = len([f for f in facturas if f.estado == models.EstadoFactura.PENDIENTE])
        facturas_pagadas = len([f for f in facturas if f.estado == models.EstadoFactura.PAGADO])
        
        monto_total_pendiente = sum(
            f.monto for f in facturas if f.estado == models.EstadoFactura.PENDIENTE
        )
        monto_total_pagado = sum(
            f.monto for f in facturas if f.estado == models.EstadoFactura.PAGADO
        )
        
        return schemas.EstadisticasUsuario(
            total_facturas=total_facturas,
            facturas_pendientes=facturas_pendientes,
            facturas_pagadas=facturas_pagadas,
            monto_total_pendiente=monto_total_pendiente,
            monto_total_pagado=monto_total_pagado
        )

class ValidationController:
    """Controlador para validaciones de negocio."""
    
    @staticmethod
    def validate_factura_payment_eligibility(factura: models.Factura) -> bool:
        """
        Valida si una factura es elegible para pago.
        Incluye reglas de negocio específicas.
        """
        # Debe estar en estado PENDIENTE
        if factura.estado != models.EstadoFactura.PENDIENTE:
            return False
        
        # El monto debe ser mayor a 0
        if factura.monto <= 0:
            return False
        
        # Podrías agregar más validaciones aquí:
        # - Verificar que no esté muy vencida
        # - Verificar límites de pago
        # - Etc.
        
        return True
    
    @staticmethod
    def validate_user_can_access_factura(user_id: int, factura: models.Factura) -> bool:
        """
        Valida que un usuario puede acceder a una factura específica.
        """
        return factura.usuario_id == user_id
