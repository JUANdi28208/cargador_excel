from sqlalchemy.orm import Session
from app.models.database import ExcelUpload, ExcelSheet, ProcessedData
from app.schemas.excel_schemas import ExcelUploadRequest, ValidationResponse
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

class ExcelService:
    
    @staticmethod
    def validate_excel_data(sheets_data: ExcelUploadRequest) -> ValidationResponse:
        """
        Valida los datos del Excel antes de guardar en la base de datos
        """
        errors = []
        warnings = []
        
        for sheet in sheets_data.sheets:
            if not sheet.data:
                errors.append(f"La hoja '{sheet.name}' está vacía")
                continue
                
            # Validar que haya al menos una fila de datos
            if len(sheet.data) == 0:
                errors.append(f"La hoja '{sheet.name}' no tiene datos")
                continue
                
            # Validar que todas las filas tengan la misma estructura
            first_row_keys = set(sheet.data[0].keys()) if sheet.data else set()
            for i, row in enumerate(sheet.data):
                current_keys = set(row.keys())
                if current_keys != first_row_keys:
                    warnings.append(f"La hoja '{sheet.name}' tiene estructura inconsistente en la fila {i+1}")
                    
            # Validar tipos de datos numéricos
            for i, row in enumerate(sheet.data):
                for key, value in row.items():
                    if value and isinstance(value, str):
                        # Intentar convertir a número si es posible
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            pass  # No es numérico, está bien
                            
        success = len(errors) == 0
        message = "Validación exitosa" if success else "Errores encontrados en la validación"
        
        return ValidationResponse(
            success=success,
            message=message,
            errors=errors if errors else None,
            warnings=warnings if warnings else None
        )
    
    @staticmethod
    def save_excel_data(db: Session, sheets_data: ExcelUploadRequest, filename: str = "uploaded_file") -> int:
        """
        Guarda los datos del Excel en la base de datos
        """
        # Crear registro de upload
        upload = ExcelUpload(
            filename=filename,
            upload_date=datetime.utcnow(),
            status="processed"
        )
        db.add(upload)
        db.flush()  # Para obtener el ID
        
        # Guardar cada hoja
        for sheet in sheets_data.sheets:
            excel_sheet = ExcelSheet(
                upload_id=upload.id,
                sheet_name=sheet.name,
                data=sheet.data
            )
            db.add(excel_sheet)
            
            # Procesar datos para análisis (ejemplo)
            ExcelService._process_sheet_data(db, upload.id, sheet.name, sheet.data)
        
        db.commit()
        return upload.id
    
    @staticmethod
    def _process_sheet_data(db: Session, upload_id: int, sheet_name: str, data: List[Dict[str, Any]]):
        """
        Procesa los datos de la hoja para análisis y gráficos
        """
        if not data:
            return
            
        # Convertir a DataFrame para análisis
        df = pd.DataFrame(data)
        
        # Procesar columnas numéricas
        numeric_columns = df.select_dtypes(include=['number']).columns
        
        for col in numeric_columns:
            for value in df[col].dropna():
                processed_data = ProcessedData(
                    upload_id=upload_id,
                    sheet_name=sheet_name,
                    column_name=col,
                    value=float(value),
                    category=col,
                    processed_date=datetime.utcnow()
                )
                db.add(processed_data)