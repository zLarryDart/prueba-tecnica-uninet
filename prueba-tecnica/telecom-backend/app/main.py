from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas
from .database import engine
from .deps import get_db, get_current_user, create_access_token
from .controllers import AuthController, FacturaController, ValidationController

# Crea las tablas en MySQL si no existen
models.Base.metadata.create_all(bind=engine)

# Aquí definimos la instancia de FastAPI que Uvicorn cargará
app = FastAPI(
    title="Telecom API",
    description="API REST para gestión de facturas de telecomunicaciones",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/auth/login", response_model=schemas.Token, summary="Autenticación de usuario")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Autentica un usuario con username y password.
    Retorna un token JWT para acceso a endpoints protegidos.
    """
    print(f"Login attempt for username: {form_data.username}")  # Debug log
    user = AuthController.authenticate_user(form_data.username, form_data.password, db)
    if not user:
        print(f"Authentication failed for username: {form_data.username}")  # Debug log
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    print(f"Authentication successful for username: {form_data.username}")  # Debug log
    access_token = create_access_token(data={"sub": user.username})
    return schemas.Token(access_token=access_token, token_type="bearer")

@app.post("/auth/register", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED, summary="Registro de usuario")
def register(u: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en el sistema.
    Las contraseñas se cifran automáticamente con bcrypt.
    """
    return AuthController.register_user(u, db)

@app.get("/facturas/", response_model=list[schemas.Factura], summary="Consultar estado de cuenta")
def consultar_facturas(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Consulta todas las facturas asociadas al usuario autenticado.
    Retorna lista de facturas con su estado (PENDIENTE/PAGADO).
    """
    return FacturaController.get_user_facturas(current_user.id, db)

@app.get("/facturas/pendientes", response_model=list[schemas.Factura], summary="Consultar facturas pendientes")
def consultar_facturas_pendientes(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Consulta solo las facturas pendientes del usuario autenticado.
    Ordenadas por fecha de vencimiento (próximas a vencer primero).
    """
    from . import crud
    return crud.get_facturas_pendientes(db, current_user.id)

@app.get("/facturas/pagadas", response_model=list[schemas.Factura], summary="Consultar facturas pagadas")
def consultar_facturas_pagadas(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Consulta solo las facturas pagadas del usuario autenticado.
    Ordenadas por fecha de emisión (más recientes primero).
    """
    from . import crud
    return crud.get_facturas_pagadas(db, current_user.id)

@app.get("/facturas/estadisticas", response_model=schemas.EstadisticasUsuario, summary="Estadísticas de facturas")
def obtener_estadisticas(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas de facturas del usuario autenticado.
    Incluye totales, montos pendientes y pagados.
    """
    return FacturaController.get_user_statistics(current_user.id, db)

@app.get("/facturas/resumen", response_model=schemas.ResumenFacturas, summary="Resumen separado de facturas")
def obtener_resumen_facturas(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene un resumen completo con facturas separadas por estado.
    Útil para mostrar en pestañas separadas en la aplicación móvil.
    """
    from . import crud
    
    facturas_pendientes = crud.get_facturas_pendientes(db, current_user.id)
    facturas_pagadas = crud.get_facturas_pagadas(db, current_user.id)
    estadisticas = crud.get_user_statistics(db, current_user.id)
    
    return {
        "facturas_pendientes": facturas_pendientes,
        "facturas_pagadas": facturas_pagadas,
        "estadisticas": estadisticas
    }

@app.get("/facturas/{factura_id}", response_model=schemas.FacturaDetallada, summary="Consultar factura específica")
def obtener_factura(
    factura_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene los detalles completos de una factura específica.
    Solo el propietario puede acceder a sus facturas.
    Incluye información adicional como días para vencimiento.
    """
    from datetime import datetime
    
    factura = FacturaController.get_factura_by_id(factura_id, current_user.id, db)
    
    # Calcular días para vencimiento si está pendiente
    dias_vencimiento = None
    if factura.estado == "PENDIENTE" and factura.fecha_vencimiento:
        dias_vencimiento = (factura.fecha_vencimiento - datetime.now().date()).days
    
    # Crear respuesta detallada
    return {
        **factura.__dict__,
        "dias_para_vencimiento": dias_vencimiento,
        "puede_pagar": factura.estado == "PENDIENTE",
        "monto_formateado": f"${factura.monto:.2f}"
    }

@app.post("/facturas/{factura_id}/pagar", response_model=schemas.PagoResponse, summary="Registrar pago")
def registrar_pago(
    factura_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registra el pago de una factura, actualizando su estado a PAGADO.
    Solo el propietario de la factura puede registrar el pago.
    Incluye validaciones de negocio completas.
    """
    factura_actualizada = FacturaController.process_payment(factura_id, current_user.id, db)
    
    return {
        "success": True,
        "message": f"Pago registrado exitosamente para factura {factura_actualizada.numero_factura}",
        "factura": factura_actualizada,
        "monto_pagado": f"${factura_actualizada.monto:.2f}",
        "fecha_pago": factura_actualizada.updated_at
    }

@app.get("/health", response_model=schemas.Message, summary="Health Check")
def health_check():
    """Endpoint de verificación de estado del servicio."""
    return schemas.Message(message="Servicio funcionando correctamente", success=True)

@app.get("/debug/users", summary="Listar todos los usuarios (solo para debug)")
def list_all_users(db: Session = Depends(get_db)):
    """
    Lista todos los usuarios en la base de datos.
    Solo para propósitos de debugging.
    """
    users = db.query(models.Usuario).all()
    return [{"id": u.id, "username": u.username, "nombre_completo": u.nombre_completo, "created_at": u.created_at} for u in users]

@app.post("/facturas/test", response_model=schemas.Factura, summary="Crear factura de prueba (solo para testing)")
def crear_factura_prueba(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea una factura de prueba para el usuario autenticado.
    Solo para fines de testing.
    """
    import random
    from datetime import datetime, timedelta
    from .models import Factura, EstadoFactura
    
    # Crear factura de prueba con datos aleatorios
    factura = Factura(
        numero_factura=f"FAC-{random.randint(1000, 9999)}",
        usuario_id=current_user.id,
        monto=random.uniform(50.0, 500.0),
        fecha_emision=datetime.utcnow(),
        fecha_vencimiento=datetime.utcnow() + timedelta(days=random.randint(1, 30)),
        estado=EstadoFactura.PENDIENTE,
        descripcion=f"Factura de servicios de telecomunicaciones"
    )
    
    db.add(factura)
    db.commit()
    db.refresh(factura)
    
    return factura

@app.post("/facturas/create", response_model=schemas.Factura, summary="Crear factura personalizada")
def crear_factura_personalizada(
    factura_data: schemas.FacturaCreateSimple,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea una factura personalizada para el usuario autenticado.
    Permite especificar monto, descripción y días hasta vencimiento.
    """
    import random
    from datetime import datetime, timedelta
    from .models import Factura, EstadoFactura
    
    # Crear factura personalizada
    factura = Factura(
        numero_factura=f"FAC-{random.randint(1000, 9999)}",
        usuario_id=current_user.id,
        monto=factura_data.monto,
        fecha_emision=datetime.utcnow(),
        fecha_vencimiento=datetime.utcnow() + timedelta(days=factura_data.dias_vencimiento or 30),
        estado=EstadoFactura.PENDIENTE,
        descripcion=factura_data.descripcion
    )
    
    db.add(factura)
    db.commit()
    db.refresh(factura)
    
    return factura
