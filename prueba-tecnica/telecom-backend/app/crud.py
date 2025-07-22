from sqlalchemy.orm import Session
from passlib.context import CryptContext
from . import models, schemas

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user(db: Session, username: str):
    """Obtiene un usuario por username."""
    return db.query(models.Usuario).filter(models.Usuario.username == username).first()

def get_user_by_id(db: Session, user_id: int):
    """Obtiene un usuario por ID."""
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()

def create_user(db: Session, u: schemas.UsuarioCreate):
    """
    Crea un nuevo usuario con contraseña cifrada.
    La contraseña se hashea usando bcrypt antes de guardarse.
    """
    hashed = pwd_ctx.hash(u.password)
    db_user = models.Usuario(
        username=u.username, 
        password_hash=hashed,
        email=u.email,
        nombre_completo=u.nombre_completo
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_pw(plain: str, hashed: str):
    """Verifica si una contraseña en texto plano coincide con el hash."""
    return pwd_ctx.verify(plain, hashed)

def list_facturas(db: Session, user_id: int):
    """
    Lista todas las facturas de un usuario específico.
    Ordenadas por fecha de emisión descendente.
    """
    return db.query(models.Factura)\
             .filter(models.Factura.usuario_id == user_id)\
             .order_by(models.Factura.fecha_emision.desc())\
             .all()

def get_factura_by_id(db: Session, factura_id: int):
    """Obtiene una factura específica por ID."""
    return db.query(models.Factura).filter(models.Factura.id == factura_id).first()

def pay_factura(db: Session, factura_id: int):
    """
    Marca una factura como pagada.
    Cambia el estado de PENDIENTE a PAGADO.
    """
    factura = db.query(models.Factura).filter(models.Factura.id == factura_id).first()
    if factura and factura.estado == models.EstadoFactura.PENDIENTE:
        factura.estado = models.EstadoFactura.PAGADO
        db.commit()
        db.refresh(factura)
    return factura

def get_facturas_pendientes(db: Session, user_id: int):
    """Obtiene solo las facturas pendientes de un usuario."""
    return db.query(models.Factura)\
             .filter(models.Factura.usuario_id == user_id)\
             .filter(models.Factura.estado == models.EstadoFactura.PENDIENTE)\
             .order_by(models.Factura.fecha_vencimiento.asc())\
             .all()

def get_facturas_pagadas(db: Session, user_id: int):
    """Obtiene solo las facturas pagadas de un usuario."""
    return db.query(models.Factura)\
             .filter(models.Factura.usuario_id == user_id)\
             .filter(models.Factura.estado == models.EstadoFactura.PAGADO)\
             .order_by(models.Factura.fecha_emision.desc())\
             .all()

def get_user_statistics(db: Session, user_id: int):
    """
    Obtiene estadísticas completas del usuario.
    Incluye conteos y montos totales por estado.
    """
    from sqlalchemy import func
    
    # Estadísticas generales
    total_facturas = db.query(models.Factura)\
                      .filter(models.Factura.usuario_id == user_id)\
                      .count()
    
    facturas_pendientes = db.query(models.Factura)\
                           .filter(models.Factura.usuario_id == user_id)\
                           .filter(models.Factura.estado == models.EstadoFactura.PENDIENTE)\
                           .count()
    
    facturas_pagadas = db.query(models.Factura)\
                        .filter(models.Factura.usuario_id == user_id)\
                        .filter(models.Factura.estado == models.EstadoFactura.PAGADO)\
                        .count()
    
    # Montos totales
    monto_pendiente = db.query(func.sum(models.Factura.monto))\
                       .filter(models.Factura.usuario_id == user_id)\
                       .filter(models.Factura.estado == models.EstadoFactura.PENDIENTE)\
                       .scalar() or 0
    
    monto_pagado = db.query(func.sum(models.Factura.monto))\
                    .filter(models.Factura.usuario_id == user_id)\
                    .filter(models.Factura.estado == models.EstadoFactura.PAGADO)\
                    .scalar() or 0
    
    return {
        "total_facturas": total_facturas,
        "facturas_pendientes": facturas_pendientes,
        "facturas_pagadas": facturas_pagadas,
        "monto_total_pendiente": str(monto_pendiente),
        "monto_total_pagado": str(monto_pagado)
    }
