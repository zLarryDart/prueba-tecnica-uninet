"""
Script para recrear las tablas de la base de datos
"""
from app.database import engine
from app import models

def recreate_tables():
    """Elimina y recrea todas las tablas"""
    print("Eliminando tablas existentes...")
    models.Base.metadata.drop_all(bind=engine)
    
    print("Creando nuevas tablas...")
    models.Base.metadata.create_all(bind=engine)
    
    print("Tablas recreadas exitosamente!")

if __name__ == "__main__":
    recreate_tables()
