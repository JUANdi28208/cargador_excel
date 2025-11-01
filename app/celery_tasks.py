from celery import Celery
from .excel_processor import DynamicExcelProcessor
from .database import SessionLocal
from typing import List, Dict, Any
import io

# Configuración de Celery
celery_app = Celery('excel_tasks', broker='redis://localhost:6379/0')

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Instancia del procesador
processor = DynamicExcelProcessor()

@celery_app.task(bind=True)
def process_excel_task(self, file_content: bytes, filename: str, selected_sheets: List[str] = None) -> Dict[str, Any]:
    """Tarea para procesar un archivo Excel"""
    try:
        db = SessionLocal()
        result = processor.process_any_excel(file_content, filename, db, selected_sheets)
        db.close()
        return result
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task
def validate_excel_task(file_content: bytes, filename: str) -> Dict[str, Any]:
    """Tarea para validar un archivo Excel"""
    return processor.validate_excel_file(file_content, filename)

@celery_app.task
def get_sheet_preview_task(file_content: bytes, sheet_name: str, max_rows: int = 5) -> Dict[str, Any]:
    """Tarea para obtener una vista previa de una hoja de Excel"""
    return processor.get_sheet_preview(file_content, sheet_name, max_rows)

@celery_app.task
def get_data_stats_task() -> Dict[str, Any]:
    """Tarea para obtener estadísticas de los datos cargados"""
    db = SessionLocal()
    stats = processor.get_data_stats(db)
    db.close()
    return stats

@celery_app.task
def get_chart_data_task(filename: str, x_axis: str, y_axis: str, chart_type: str = "bar", group_by: str = None) -> Dict[str, Any]:
    """Tarea para obtener datos formateados para gráficos"""
    db = SessionLocal()
    result = processor.get_chart_data(db, filename, x_axis, y_axis, chart_type, group_by)
    db.close()
    return result

@celery_app.task
def get_available_columns_task(filename: str) -> Dict[str, Any]:
    """Tarea para obtener columnas disponibles para análisis y gráficos"""
    db = SessionLocal()
    result = processor.get_available_columns(db, filename)
    db.close()
    return result