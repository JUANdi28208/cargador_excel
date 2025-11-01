# config.py
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Configuración de la aplicación"""
    
    # Configuración de la aplicación
    APP_TITLE: str = "SENA Excel Processing API"
    APP_DESCRIPTION: str = "API para procesamiento y análisis de archivos Excel"
    APP_VERSION: str = "1.0.0"
    
    # Configuración CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4200",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4200",
        "*"  # Para desarrollo
    ]
    
    # Configuración de base de datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:password123@mysql:3306/excel_uploader")
    
    # Configuración de la aplicación
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

# Instancia global de configuración
settings = Settings()