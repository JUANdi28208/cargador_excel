from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
import os
from pathlib import Path

from . import models, schemas, upload
from .database import engine, get_db

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Excel Uploader API - Dinámico", version="2.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    frontend_path = Path("frontend/index.html")
    if frontend_path.exists():
        return frontend_path.read_text(encoding='utf-8')
    return """
    <h1>Excel Uploader API - Versión Dinámica</h1>
    <p>acepta CUALQUIER archivo Excel con cualquier estructura</p>
    <p><a href="/docs">Ver documentación de la API</a></p>
    """

@app.post("/upload/", response_model=schemas.UploadResponse)
async def upload_excel_file(
    file: UploadFile = File(...),
    selected_sheets: str = Form(None),  # Cambiado de List[str] a str
    db: Session = Depends(get_db)
):
    print(f" INICIANDO UPLOAD")
    print(f" Archivo: {file.filename}")
    print(f" Hojas seleccionadas (raw): {selected_sheets}")
    
    # Procesar el string a lista
    selected_sheets_list = None
    if selected_sheets:
        # Si viene como JSON string, parsearlo
        if selected_sheets.startswith('['):
            try:
                import json
                selected_sheets_list = json.loads(selected_sheets)
            except:
                selected_sheets_list = [sheet.strip() for sheet in selected_sheets.split(',')]
        else:
            # Si viene como string simple, dividir por comas
            selected_sheets_list = [sheet.strip() for sheet in selected_sheets.split(',') if sheet.strip()]
    
    print(f" Hojas seleccionadas (procesadas): {selected_sheets_list}")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel")
    
    content = await file.read()
    print(f" Tamaño del archivo: {len(content)} bytes")
    
    result = upload.upload_processor.process_any_excel(content, file.filename, db, selected_sheets_list)
    
    print(f" Resultado del procesamiento: {result.get('success')}")
    
    if not result["success"]:
        detail = {"error": result.get("error")}
        if "blank_sheets" in result:
            detail["blank_sheets"] = result.get("blank_sheets")
        if "skipped_sheets" in result:
            detail["skipped_sheets"] = result.get("skipped_sheets")
        raise HTTPException(status_code=400, detail=detail)
    
    return schemas.UploadResponse(
        message=result["message"],
        total_records=result["total_rows"],
        processed_records=result["processed_rows"],
        sheets_processed=result["sheets_processed"],
        columns_detected=result["columns_detected"],
        sample_data=result["sample_data"],
        blank_sheets=result.get("blank_sheets"),
        skipped_sheets=result.get("skipped_sheets")
    )

@app.post("/validate/")
async def validate_excel(file: UploadFile = File(...)):
    """Endpoint para validar qué hojas están vacías antes de subir."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel")

    content = await file.read()
    result = upload.upload_processor.validate_excel_file(content, file.filename)

    # Siempre devolver 200, usar "valid" para indicar estado
    if not result.get("valid"):
        return {
            "valid": False,
            "error": result.get("error"),
            "sheet_info": result.get("sheet_info", {}),
            "empty_sheets": result.get("empty_sheets", []),
            "non_empty_sheets": result.get("non_empty_sheets", []),
            "has_empty_sheets": result.get("has_empty_sheets", False),
            "sheet_names": result.get("sheet_names", []),
            "sheets": result.get("sheets", 0),
            "total_rows": result.get("total_rows", 0)
        }

    return {
        "valid": True,
        "sheets": result.get("sheets"),
        "total_rows": result.get("total_rows"),
        "sheet_names": result.get("sheet_names"),
        "sheet_info": result.get("sheet_info"),
        "empty_sheets": result.get("empty_sheets", []),
        "non_empty_sheets": result.get("non_empty_sheets", []),
        "has_empty_sheets": result.get("has_empty_sheets", False)
    }

@app.post("/preview-sheet/")
async def preview_sheet(
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
    max_rows: int = Form(5)
):
    """Endpoint para previsualizar una hoja específica de un archivo Excel."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel")

    content = await file.read()
    result = upload.upload_processor.get_sheet_preview(content, sheet_name, max_rows)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

@app.get("/progress/")
async def get_upload_progress():
    progress = upload.upload_processor.get_progress()
    return {"progress": progress}

@app.get("/data/")
async def get_uploaded_data(db: Session = Depends(get_db)):
    data = db.query(models.ExcelData).all()
    return data

@app.get("/data/{filename}")
async def get_data_by_filename(filename: str, db: Session = Depends(get_db)):
    data = db.query(models.ExcelData).filter(models.ExcelData.filename == filename).all()
    return data

@app.get("/files/")
async def get_uploaded_files(db: Session = Depends(get_db)):
    files = db.query(models.ExcelData.filename).distinct().all()
    return {"files": [f[0] for f in files]}

@app.get("/health/")
async def health_check():
    return {"status": "healthy", "service": "excel-uploader-dynamic"}