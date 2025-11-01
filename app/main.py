from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form, Request
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import datetime
import time
import logging
import math
from decimal import Decimal
from pydantic import BaseModel

# Importaciones ABSOLUTAS para Docker (sin puntos)
import models
import schemas
from excel_processor import upload_processor
from database import engine, get_db, Base
from upload.upload_processor import validate_excel_file, get_sheet_preview, process_any_excel, get_data_stats, get_progress
from config import settings
from services import build_response, DatabaseLogger

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Esquemas Pydantic para los endpoints de Angular
class SheetData(BaseModel):
    name: str
    data: List[Dict[str, Any]]

class ExcelUploadRequest(BaseModel):
    sheets: List[SheetData]

class ValidationResponse(BaseModel):
    success: bool
    message: str
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Configuración de la aplicación
app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(f"Method: {request.method} | Path: {request.url.path} | Status: {response.status_code} | Duration: {process_time:.2f}ms")
    return response

# Endpoints principales
@app.get("/", tags=["Health"])
async def read_root():
    """Endpoint raíz - Información del API"""
    return build_response(
        success=True,
        message="SENA Excel Backend API - Versión Docker",
        data={
            "service": "Excel Processing API",
            "version": settings.APP_VERSION,
            "description": settings.APP_DESCRIPTION,
            "documentation": "/docs"
        }
    )

@app.get("/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """Health Check del sistema"""
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return build_response(
        success=db_status == "healthy",
        message="Health check completed",
        data={
            "status": "healthy" if db_status == "healthy" else "degraded",
            "database": db_status,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "services": {
                "api": "healthy",
                "database": db_status,
                "logging": "healthy"
            }
        }
    )

@app.get("/status", tags=["Health"])
async def system_status(db: Session = Depends(get_db)):
    """Estado detallado del sistema"""
    stats_result = upload_processor.get_data_stats(db)
    return build_response(
        success="error" not in stats_result,
        message="System status retrieved",
        data=stats_result if "error" not in stats_result else None,
        errors=[stats_result["error"]] if "error" in stats_result else None
    )

# ENDPOINTS PARA ANGULAR - Compatibilidad con el frontend
@app.post("/api/excel/validate", response_model=ValidationResponse, tags=["Excel API"])
async def validate_excel_data_api(request: ExcelUploadRequest):
    """Endpoint de validación para el frontend Angular"""
    try:
        errors = []
        warnings = []
        
        for sheet in request.sheets:
            if not sheet.data:
                errors.append(f"La hoja '{sheet.name}' está vacía")
                continue
                
            if len(sheet.data) == 0:
                errors.append(f"La hoja '{sheet.name}' no tiene datos")
                continue
                
            # Validar estructura consistente
            if sheet.data:
                first_row_keys = set(sheet.data[0].keys())
                for i, row in enumerate(sheet.data):
                    current_keys = set(row.keys())
                    if current_keys != first_row_keys:
                        warnings.append(f"La hoja '{sheet.name}' tiene estructura inconsistente en la fila {i+1}")
        
        success = len(errors) == 0
        message = "Validación exitosa" if success else "Errores encontrados en la validación"
        
        return ValidationResponse(
            success=success,
            message=message,
            errors=errors if errors else None,
            warnings=warnings if warnings else None
        )
        
    except Exception as e:
        return ValidationResponse(
            success=False,
            message=f"Error en validación: {str(e)}",
            errors=[str(e)]
        )

@app.post("/api/excel/upload", tags=["Excel API"])
async def upload_excel_data_api(request: ExcelUploadRequest, db: Session = Depends(get_db)):
    """Endpoint de carga para el frontend Angular"""
    try:
        total_records = 0
        sheets_processed = 0
        all_records = []
        
        for sheet in request.sheets:
            if not sheet.data or len(sheet.data) == 0:
                continue
                
            # Procesar cada fila de la hoja
            sheet_records = []
            for row in sheet.data:
                try:
                    # Crear registro para la base de datos
                    excel_record = models.ExcelData(
                        filename="uploaded_from_angular",
                        sheet_name=sheet.name,
                        row_data=row
                    )
                    sheet_records.append(excel_record)
                except Exception as e:
                    logger.warning(f"Error procesando fila en hoja {sheet.name}: {e}")
                    continue
            
            # Guardar registros de esta hoja
            if sheet_records:
                db.add_all(sheet_records)
                all_records.extend(sheet_records)
                sheets_processed += 1
                total_records += len(sheet_records)
        
        # Hacer commit de todos los registros
        db.commit()
        
        # Log en base de datos
        DatabaseLogger.log_to_db(
            db, "INFO", "excel_upload_angular", 
            f"Excel procesado desde Angular: {sheets_processed} hojas, {total_records} registros",
            {
                "sheets_processed": sheets_processed,
                "total_records": total_records,
                "source": "angular_frontend"
            }
        )
        
        return build_response(
            success=True,
            message=f"Datos cargados exitosamente: {total_records} registros en {sheets_processed} hojas",
            data={
                "total_records": total_records,
                "sheets_processed": sheets_processed,
                "records_processed": len(all_records)
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error en upload desde Angular: {e}")
        return build_response(
            success=False,
            message=f"Error cargando datos: {str(e)}",
            errors=[str(e)],
            status_code=500
        )

# ENDPOINTS DE GRÁFICOS NUEVOS
@app.get("/api/excel/temporal-chart-data", tags=["Charts"])
async def get_temporal_chart_data(db: Session = Depends(get_db)):
    """Obtener datos para gráficos de evolución temporal"""
    try:
        # Obtener todos los registros
        records = db.query(models.ExcelData).all()
        
        if not records:
            return build_response(
                success=False,
                message="No hay datos para generar gráficos temporales",
                data=None
            )
        
        # Buscar patrones de datos temporales (meses vs valores)
        temporal_data = {}
        month_patterns = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december'
        ]
        
        for record in records:
            for column_name, value in record.row_data.items():
                col_lower = column_name.lower()
                
                # Buscar si la columna contiene nombres de meses
                is_month_column = any(month in col_lower for month in month_patterns)
                is_value_column = any(keyword in col_lower for keyword in 
                                    ['usuario', 'user', 'valor', 'value', 'numero', 'number', 'cantidad', 'total'])
                
                # Si es una columna de valor numérico
                if is_value_column or (value and str(value).isdigit()):
                    try:
                        numeric_value = float(value)
                        sheet_name = record.sheet_name
                        
                        if sheet_name not in temporal_data:
                            temporal_data[sheet_name] = {}
                        
                        # Usar el nombre de la columna como categoría
                        temporal_data[sheet_name][column_name] = numeric_value
                        
                    except (ValueError, TypeError):
                        continue
        
        # Si encontramos datos temporales, organizarlos
        if temporal_data:
            # Tomar la primera hoja con datos
            first_sheet = list(temporal_data.keys())[0]
            data = temporal_data[first_sheet]
            
            # Ordenar por nombres de meses si es posible
            ordered_labels = []
            ordered_values = []
            
            # Intentar ordenar por meses
            month_order = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }
            
            # Primero intentar ordenar por meses conocidos
            month_items = []
            other_items = []
            
            for label, value in data.items():
                label_lower = label.lower()
                found_month = None
                for month, order in month_order.items():
                    if month in label_lower:
                        found_month = order
                        break
                
                if found_month:
                    month_items.append((found_month, label, value))
                else:
                    other_items.append((label, value))
            
            # Ordenar meses y agregar otros
            month_items.sort()
            for order, label, value in month_items:
                ordered_labels.append(label)
                ordered_values.append(value)
            
            for label, value in other_items:
                ordered_labels.append(label)
                ordered_values.append(value)
            
            # Si no hay suficientes datos ordenados, usar todos sin ordenar
            if not ordered_labels:
                ordered_labels = list(data.keys())
                ordered_values = list(data.values())
            
            chart_data = {
                "temporal_chart": {
                    "labels": ordered_labels,
                    "datasets": [{
                        "label": f"Evolución - {first_sheet}",
                        "data": ordered_values,
                        "borderColor": '#1976d2',
                        "backgroundColor": 'rgba(25, 118, 210, 0.2)',
                        "borderWidth": 3,
                        "tension": 0.3,
                        "fill": True
                    }]
                },
                "summary": {
                    "total_data_points": len(ordered_values),
                    "average_value": round(sum(ordered_values) / len(ordered_values), 2),
                    "max_value": max(ordered_values),
                    "min_value": min(ordered_values),
                    "trend": "creciente" if ordered_values[-1] > ordered_values[0] else "decreciente"
                }
            }
            
            return build_response(
                success=True,
                message="Datos temporales obtenidos exitosamente",
                data=chart_data
            )
        else:
            # Fallback a datos básicos
            return build_response(
                success=False,
                message="No se detectaron patrones de datos temporales",
                data=None
            )
            
    except Exception as e:
        logger.error(f"Error obteniendo datos temporales: {e}")
        return build_response(
            success=False,
            message="Error procesando datos temporales",
            errors=[str(e)]
        )

@app.get("/api/excel/pie-chart-data", tags=["Charts"])
async def get_pie_chart_data(db: Session = Depends(get_db)):
    """Obtener datos para gráfico de pastel con porcentajes"""
    try:
        # Obtener todos los registros
        records = db.query(models.ExcelData).all()
        
        if not records:
            return build_response(
                success=False,
                message="No hay datos para generar gráfico de pastel",
                data=None
            )
        
        # Recolectar datos para el gráfico de pastel
        pie_data = {}
        
        for record in records:
            for column_name, value in record.row_data.items():
                # Buscar datos categóricos o con nombres significativos
                col_lower = column_name.lower()
                
                # Categorías comunes para gráficos de pastel
                is_category = any(keyword in col_lower for keyword in [
                    'categoria', 'category', 'tipo', 'type', 'genero', 'gender',
                    'departamento', 'department', 'ciudad', 'city', 'pais', 'country',
                    'estado', 'status', 'nivel', 'level', 'grupo', 'group'
                ])
                
                # Si es una categoría o el valor es texto
                if is_category or (value and not str(value).replace('.', '').isdigit()):
                    category = str(value).strip()
                    if category and category.lower() not in ['', 'null', 'none', 'nan']:
                        if category not in pie_data:
                            pie_data[category] = 0
                        pie_data[category] += 1
                
                # También considerar datos numéricos con etiquetas significativas
                elif value and str(value).replace('.', '').isdigit():
                    try:
                        numeric_value = float(value)
                        # Usar el nombre de la columna como categoría si es significativo
                        if any(keyword in col_lower for keyword in [
                            'total', 'suma', 'count', 'cantidad', 'numero', 'valor'
                        ]):
                            if column_name not in pie_data:
                                pie_data[column_name] = 0
                            pie_data[column_name] += numeric_value
                    except (ValueError, TypeError):
                        continue
        
        # Si no encontramos datos categóricos, usar datos de hojas
        if not pie_data:
            sheets_data = db.query(
                models.ExcelData.sheet_name,
                func.count(models.ExcelData.id).label('record_count')
            ).group_by(models.ExcelData.sheet_name).all()
            
            for sheet in sheets_data:
                pie_data[sheet.sheet_name] = sheet.record_count
        
        # Ordenar por valor descendente y limitar a 8 categorías máximo
        sorted_data = dict(sorted(pie_data.items(), key=lambda x: x[1], reverse=True)[:8])
        
        # Calcular porcentajes
        total = sum(sorted_data.values())
        percentages = {k: round((v / total) * 100, 1) for k, v in sorted_data.items()}
        
        # Preparar datos para el gráfico
        labels = [f"{k} ({v} - {percentages[k]}%)" for k, v in sorted_data.items()]
        values = list(sorted_data.values())
        
        # Colores para el gráfico de pastel
        colors = [
            '#1976d2', '#388e3c', '#fbc02d', '#d32f2f', '#7b1fa2',
            '#0288d1', '#689f38', '#ffa000', '#d32f2f', '#512da8'
        ]
        
        chart_data = {
            "pie_chart": {
                "labels": labels,
                "datasets": [{
                    "data": values,
                    "backgroundColor": colors[:len(values)],
                    "borderColor": '#ffffff',
                    "borderWidth": 2,
                    "hoverOffset": 8
                }]
            },
            "summary": {
                "total_categories": len(sorted_data),
                "total_values": total,
                "largest_category": list(sorted_data.keys())[0],
                "largest_percentage": percentages[list(sorted_data.keys())[0]],
                "percentages": percentages
            }
        }
        
        return build_response(
            success=True,
            message="Datos para gráfico de pastel obtenidos",
            data=chart_data
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo datos para gráfico de pastel: {e}")
        return build_response(
            success=False,
            message="Error generando gráfico de pastel",
            errors=[str(e)]
        )

# ENDPOINTS ORIGINALES (mantener compatibilidad)
@app.post("/upload/", tags=["Excel"])
async def upload_excel_file(
    file: UploadFile = File(...),
    selected_sheets: str = Form(None),
    db: Session = Depends(get_db)
):
    """Cargar archivo Excel - Endpoint principal"""
    logger.info(f"Iniciando upload: {file.filename}")
    
    # Procesar selected_sheets
    selected_sheets_list = None
    if selected_sheets:
        if selected_sheets.startswith('['):
            try:
                selected_sheets_list = json.loads(selected_sheets)
            except:
                selected_sheets_list = [sheet.strip() for sheet in selected_sheets.split(',')]
        else:
            selected_sheets_list = [sheet.strip() for sheet in selected_sheets.split(',') if sheet.strip()]
    
    # Validar y procesar archivo
    content = await file.read()
    result = upload_processor.process_any_excel(content, file.filename, db, selected_sheets_list)
    
    if not result["success"]:
        return build_response(
            success=False,
            message="Error procesando archivo",
            errors=[result.get("error", "Error desconocido")],
            data={
                "blank_sheets": result.get("blank_sheets", []),
                "skipped_sheets": result.get("skipped_sheets", [])
            },
            status_code=400
        )
    
    # Log en base de datos
    DatabaseLogger.log_to_db(
        db, "INFO", "excel_upload", 
        f"Excel procesado exitosamente: {file.filename}",
        {
            "filename": file.filename,
            "sheets_processed": result["sheets_processed"],
            "total_rows": result["total_rows"],
            "processed_rows": result["processed_rows"]
        }
    )
    
    return build_response(
        success=True,
        message=result["message"],
        data={
            "total_records": result["total_rows"],
            "processed_records": result["processed_rows"],
            "sheets_processed": result["sheets_processed"],
            "columns_detected": result["columns_detected"],
            "sample_data": result["sample_data"],
            "blank_sheets": result.get("blank_sheets", []),
            "skipped_sheets": result.get("skipped_sheets", []),
            "upload_id": result.get("upload_id")
        }
    )

@app.post("/validate/", tags=["Excel"])
async def validate_excel(file: UploadFile = File(...)):
    """Validar archivo Excel"""
    content = await file.read()
    validation = upload_processor.validate_excel_file(content, file.filename)
    
    return build_response(
        success=validation["valid"],
        message="Validación completada" if validation["valid"] else "Error en validación",
        data=validation if validation["valid"] else None,
        errors=[validation["error"]] if not validation["valid"] else None
    )

@app.post("/preview-sheet/", tags=["Excel"])
async def preview_sheet(
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
    max_rows: int = Form(5)
):
    """Vista previa de hoja Excel"""
    content = await file.read()
    result = upload_processor.get_sheet_preview(content, sheet_name, max_rows)
    
    return build_response(
        success=result["success"],
        message="Vista previa generada" if result["success"] else "Error generando vista previa",
        data=result if result["success"] else None,
        errors=[result["error"]] if not result["success"] else None
    )

# Endpoint adicional para Angular
@app.post("/api/excel/preview-sheet", tags=["Excel API"])
async def preview_sheet_api(
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
    max_rows: int = Form(5)
):
    """Vista previa de hoja Excel - versión API"""
    content = await file.read()
    result = upload_processor.get_sheet_preview(content, sheet_name, max_rows)
    
    return build_response(
        success=result["success"],
        message="Vista previa generada" if result["success"] else "Error generando vista previa",
        data=result if result["success"] else None,
        errors=[result["error"]] if not result["success"] else None
    )

@app.get("/data-stats/", tags=["Excel"])
async def get_data_stats(db: Session = Depends(get_db)):
    """Estadísticas de datos cargados"""
    result = upload_processor.get_data_stats(db)
    
    return build_response(
        success="error" not in result,
        message="Estadísticas obtenidas" if "error" not in result else "Error obteniendo estadísticas",
        data=result if "error" not in result else None,
        errors=[result["error"]] if "error" in result else None
    )

@app.get("/data/", tags=["Data"])
async def get_uploaded_data(db: Session = Depends(get_db)):
    """Obtener todos los datos cargados"""
    try:
        from models import ExcelData  # Importación local para evitar problemas circulares
        data = db.query(ExcelData).all()
        return build_response(
            success=True,
            message="Datos obtenidos exitosamente",
            data={
                "records": [
                    {
                        "id": item.id, 
                        "filename": item.filename, 
                        "sheet_name": item.sheet_name,
                        "row_data": item.row_data,
                        "upload_date": item.upload_date.isoformat()
                    } for item in data
                ],
                "total": len(data)
            }
        )
    except Exception as e:
        return build_response(
            success=False,
            message="Error obteniendo datos",
            errors=[str(e)]
        )

@app.get("/files/", tags=["Data"])
async def get_uploaded_files(db: Session = Depends(get_db)):
    """Obtener lista de archivos cargados"""
    try:
        from models import ExcelData  # Importación local
        files = db.query(ExcelData.filename).distinct().all()
        return build_response(
            success=True,
            message="Archivos obtenidos exitosamente",
            data={"files": [f[0] for f in files]}
        )
    except Exception as e:
        return build_response(
            success=False,
            message="Error obteniendo archivos",
            errors=[str(e)]
        )

@app.get("/progress/", tags=["System"])
async def get_upload_progress():
    """Obtener progreso del upload actual"""
    progress = upload_processor.get_progress()
    return build_response(
        success=True,
        message="Progreso obtenido",
        data={"progress": progress}
    )

# Manejo global de excepciones
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=build_response(
            success=False,
            message="Error en la solicitud",
            errors=[exc.detail],
            status_code=exc.status_code
        )
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception: {str(exc)} - Path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content=build_response(
            success=False,
            message="Error interno del servidor",
            errors=[str(exc)],
            status_code=500
        )
    )

# Para desarrollo local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)