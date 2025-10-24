from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List

class ExcelDataBase(BaseModel):
    filename: str
    sheet_name: str
    row_data: Dict[str, Any]  # Datos dinámicos

class ExcelDataCreate(ExcelDataBase):
    pass

class ExcelData(ExcelDataBase):
    id: int
    upload_date: datetime
    
    class Config:
        from_attributes = True

class SheetInfo(BaseModel):
    empty: bool
    rows: int
    columns: List[str]

class ValidationResponse(BaseModel):
    valid: bool
    sheets: Optional[int] = None
    total_rows: Optional[int] = None
    sheets_names: Optional[List[str]] = None
    sheet_info: Optional[Dict[str, SheetInfo]] = None
    error: Optional[str] = None
    has_empty_sheets: Optional[bool] = None
    empty_sheets: Optional[List[str]] = None
    non_empty_sheets: Optional[List[str]] = None


class UploadResponse(BaseModel):
    message: str
    total_records: int
    processed_records: int
    sheets_processed: int
    columns_detected: Dict[str, List[str]]  # Columnas por hoja
    sample_data: List[Dict[str, Any]]  # Datos de muestra
    blank_sheets: Optional[List[str]] = None  # Hojas detectadas como vacías (si las hay)
    skipped_sheets: Optional[List[str]] = None  # Hojas que fueron omitidas