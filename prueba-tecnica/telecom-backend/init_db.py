from app.database import SessionLocal, engine
from app import models, crud, schemas
from datetime import date

# Crear las tablas
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Crear usuario de prueba
if not crud.get_user(db, "admin"):
    user_data = schemas.UsuarioCreate(username="admin", password="admin123")
    user = crud.create_user(db, user_data)
    print(f"Usuario creado: {user.username}")
    
    # Crear facturas de prueba
    facturas = [
        models.Factura(
            usuario_id=user.id,
            fecha_emision=date(2024, 1, 15),
            monto=150.50,
            estado=models.EstadoFactura.PENDIENTE
        ),
        models.Factura(
            usuario_id=user.id,
            fecha_emision=date(2024, 2, 15),
            monto=220.75,
            estado=models.EstadoFactura.PAGADO
        ),
        models.Factura(
            usuario_id=user.id,
            fecha_emision=date(2024, 3, 15),
            monto=185.00,
            estado=models.EstadoFactura.PENDIENTE
        )
    ]
    
    for factura in facturas:
        db.add(factura)
    
    db.commit()
    print("Facturas de prueba creadas")
else:
    print("Usuario admin ya existe")

db.close()
print("Base de datos inicializada correctamente")
