# services/__init__.py
import datetime
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

def build_response(
    success: bool = True, 
    message: str = "", 
    data: Any = None, 
    errors: List[str] = None, 
    status_code: int = 200
) -> Dict[str, Any]:
    """
    Construye una respuesta estándar para la API
    """
    response = {
        "success": success,
        "message": message,
        "data": data or {},
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    
    if errors:
        response["errors"] = errors if isinstance(errors, list) else [errors]
    
    return response

class DatabaseLogger:
    """
    Logger para guardar eventos en la base de datos
    """
    
    @staticmethod
    def log_to_db(
        db: Session, 
        level: str, 
        category: str, 
        message: str, 
        details: Dict[str, Any] = None
    ):
        """
        Log simplificado a base de datos
        """
        try:
            # Por ahora solo logueamos al logger regular
            # Puedes expandir esto para guardar en una tabla de logs en la BD
            logger = logging.getLogger('database')
            log_message = f"[{category}] {message}"
            
            if details:
                log_message += f" | Details: {details}"
            
            if level == "INFO":
                logger.info(log_message)
            elif level == "ERROR":
                logger.error(log_message)
            elif level == "WARNING":
                logger.warning(log_message)
            else:
                logger.debug(log_message)
                
        except Exception as e:
            # Fallback a logging regular si falla
            logging.error(f"Error en DatabaseLogger: {e} | Original: {message}")