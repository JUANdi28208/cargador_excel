import pandas as pd
from sqlalchemy.orm import Session
from . import models, schemas
import io
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DynamicExcelProcessor:
    def __init__(self):
        self.progress = 0
        self.total_rows = 0
        self.processed_rows = 0

    def is_sheet_empty(self, df: pd.DataFrame) -> bool:
        """Determina si una hoja está vacía (todas las filas y columnas vacías)"""
        if df.empty:
            return True
        # Eliminar filas donde todas las columnas son NaN
        df_cleaned = df.dropna(how='all')

        # Si después de limpiar no quedan filas, está vacía
        if df_cleaned.empty:
            return True
        
        # Verificar si todas las celdas son NaN
        if df_cleaned.isna().all().all():
            return True
        return False

    def validate_excel_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Validar el archivo Excel y detectar hojas vacías antes de procesar"""
        try:
            # Verificar que el archivo no esté vacío
            if len(file_content) == 0:
                return {
                    "valid": False,
                    "error": "El archivo está vacío"
                }
            
            # Verificar que sea un Excel válido
            try:
                excel_file = io.BytesIO(file_content)
                excel_data = pd.ExcelFile(excel_file)
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"El archivo no es un Excel válido: {str(e)}"
                }
            
            # Verificar que tenga al menos una hoja
            sheet_names = excel_data.sheet_names
            if not sheet_names:
                return {
                    "valid": False,
                    "error": "El archivo Excel no contiene hojas"
                }

            # Para cada hoja, detectar si está vacía
            sheet_info: Dict[str, Dict[str, Any]] = {}
            has_data = False
            total_rows = 0
            empty_sheets = []
            non_empty_sheets = []

            print(f" Validando {len(sheet_names)} hojas...")

            for sheet_name in sheet_names:
                try:
                    # Crear una nueva BytesIO para cada lectura
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)

                    # Verificar si la hoja está vacía
                    is_empty = self.is_sheet_empty(df)

                    # Contar filas no vacías
                    non_empty_rows = df.dropna(how='all') if not df.empty else df
                    row_count = len(non_empty_rows) 

                    sheet_info[sheet_name] = {
                        "empty": is_empty,
                        "rows": int(row_count),
                        "columns": df.columns.tolist() if not df.empty else []
                    }

                    if is_empty:
                        empty_sheets.append(sheet_name)
                        print(f"   📭 Hoja vacía: {sheet_name}")
                        logger.info(f"Hoja vacía detectada: {sheet_name}")
                    else:
                        non_empty_sheets.append(sheet_name)
                        has_data = True
                        total_rows += row_count
                        print(f"   Hoja con datos: {sheet_name} ({row_count} filas)")

                except Exception as e:
                    # En caso de error leyendo la hoja, marcarla como vacía y continuar
                    logger.error(f"Error leyendo la hoja {sheet_name}: {e}")
                    sheet_info[sheet_name] = {
                        "empty": True,
                        "rows": 0,
                        "columns": []
                    }
                    empty_sheets.append(sheet_name)
                    print(f"   Error en hoja {sheet_name}: {e}")
                    continue

            has_empty_sheets = len(empty_sheets) > 0

            print(f"Resumen validación:")
            print(f"   - Total hojas: {len(sheet_names)}")
            print(f"   - Hojas con datos: {len(non_empty_sheets)}")
            print(f"   - Hojas vacías: {len(empty_sheets)}")
            print(f"   - Total filas con datos: {total_rows}")

            # Preparar respuesta
            response = {
                "valid": True,
                "sheets": len(sheet_names),
                "total_rows": total_rows,
                "sheet_names": sheet_names,
                "sheet_info": sheet_info,
                "has_empty_sheets": has_empty_sheets,
                "empty_sheets": empty_sheets,
                "non_empty_sheets": non_empty_sheets
            }

            # Si no hay datos en ninguna hoja, marcar como inválido
            if not has_data:
                response.update({
                    "valid": False,
                    "error": "El archivo Excel no contiene datos válidos (todas las hojas están vacías)",
                })

            return response
            
        except Exception as e:
            logger.error(f"Error validando el archivo Excel: {e}")
            return {
                "valid": False,
                "error": f"Error validando el archivo: {str(e)}"
            }

    def get_sheet_preview(self, file_content: bytes, sheet_name: str, max_rows: int = 5) -> Dict[str, Any]:
        """Obtener vista previa de una hoja específica"""
        try:
            df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)

            # Limpiar datos Nan
            df = df.where(pd.notnull(df), None)

            # Obtener preview
            preview_df = df.head(max_rows)

            return {
                "success": True,
                "sheet_name": sheet_name,
                "columns": df.columns.tolist(),
                "total_rows": len(df),
                "preview_data": preview_df.to_dict('records'),
                "is_empty": self.is_sheet_empty(df)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo vista previa de la hoja {sheet_name}: {str(e)}"
            }

    def process_selected_sheets(self, file_content: bytes, filename: str, db: Session, selected_sheets: List[str]) -> Dict[str, Any]:
        """Procesar SOLO las hojas seleccionadas por el usuario"""
        try:
            print(f"INICIANDO PROCESAMIENTO SELECTIVO")
            print(f"Archivo: {filename}")
            print(f"Hojas seleccionadas para procesar: {selected_sheets}")

            # Validar el archivo primero
            validation = self.validate_excel_file(file_content, filename)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "total_rows": 0,
                    "processed_rows": 0,
                    "sheets_processed": 0,
                    "columns_detected": {},
                    "sample_data": [],
                    "skipped_sheets": []
                }
            
            # Verificar que las hojas seleccionadas existan en el archivo
            available_sheets = validation["sheet_names"]
            invalid_sheets = [sheet for sheet in selected_sheets if sheet not in available_sheets]

            if invalid_sheets:
                return {
                    "success": False,
                    "error": f"Las siguientes hojas seleccionadas no existen en el archivo: {', '.join(invalid_sheets)}",
                    "total_rows": 0,
                    "processed_rows": 0,
                    "sheets_processed": 0,
                    "columns_detected": {},
                    "sample_data": [],
                    "skipped_sheets": []
                }
            
            # Procesar solo las hojas seleccionadas
            excel_data = pd.ExcelFile(io.BytesIO(file_content))
            all_records = []
            columns_detected = {}
            sample_data = []
            skipped_sheets = []

            self.total_rows = 0
            self.processed_rows = 0

            print(f"🔍 Procesando {len(selected_sheets)} hojas seleccionadas...")

            for sheet_name in selected_sheets:
                try:
                    print(f"   Leyendo hoja: {sheet_name}")
                    
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)

                    # Verificar si la hoja está vacía
                    if self.is_sheet_empty(df):
                        skipped_sheets.append(sheet_name)
                        print(f"   📭 Hoja vacía omitida: {sheet_name}")
                        logger.info(f"Hoja vacía omitida: {sheet_name}")
                        continue

                    # Limpiar datos
                    df = df.dropna(how='all')
                    df = df.where(pd.notnull(df), None)
                    df = df.astype(object).where(pd.notnull(df), None)

                    rows_with_data = len(df)
                    print(f"    Hoja {sheet_name}: {rows_with_data} filas con datos")

                    # Guardar información de columnas
                    columns_detected[sheet_name] = df.columns.tolist()

                    # Procesar cada fila
                    sheet_records = []
                    for index, row in df.iterrows():
                        try:
                            row_dict = {str(col): (str(val) if val is not None else None) 
                                       for col, val in row.to_dict().items()}
                            
                            # Saltar filas completamente vacías
                            if not any(val for val in row_dict.values() if val is not None):
                                continue
                            
                            excel_record = models.ExcelData(
                                filename=filename,
                                sheet_name=sheet_name,
                                row_data=row_dict
                            )
                            sheet_records.append(excel_record)

                            # Guardar primeras filas como muestra (máximo 2 por hoja)
                            if len(sample_data) < 10 and len([s for s in sample_data if s.get("sheet_name") == sheet_name]) < 2:
                                sample_data.append({
                                    "sheet_name": sheet_name,
                                    "data": row_dict
                                })

                        except Exception as e:
                            logger.warning(f"Error en fila {index}, hoja {sheet_name}: {e}")
                            continue

                    # Agregar registros de esta hoja
                    all_records.extend(sheet_records)

                    # Actualizar conteos
                    non_empty = df.dropna(how='all')
                    self.total_rows += len(non_empty)
                    self.processed_rows = len(all_records)

                    print(f"   Hoja {sheet_name} procesada: {len(sheet_records)} filas guardadas")

                except Exception as e:
                    logger.error(f"Error procesando la hoja {sheet_name}: {e}")
                    skipped_sheets.append(sheet_name)
                    print(f"   Error procesando hoja {sheet_name}: {e}")
                    continue

            # Verificar que se procesaron registros
            if not all_records:
                return {
                    "success": False,
                    "error": "No se encontraron datos válidos para procesar en las hojas seleccionadas (todas las filas están vacías)",
                    "total_rows": 0,
                    "processed_rows": 0,
                    "sheets_processed": 0,
                    "columns_detected": {},
                    "sample_data": [],
                    "skipped_sheets": skipped_sheets
                }
            
            # Guardar en base de datos
            db.add_all(all_records)
            db.commit()

            sheets_processed = len(selected_sheets) - len(skipped_sheets)

            print(f"📊 RESUMEN FINAL:")
            print(f"   Hojas procesadas: {sheets_processed}")
            print(f"   Hojas saltadas: {len(skipped_sheets)}")
            print(f"   Total filas procesadas: {len(all_records)}")

            return {
                "success": True,
                "total_rows": self.total_rows,
                "processed_rows": len(all_records),
                "sheets_processed": sheets_processed,
                "columns_detected": columns_detected,
                "sample_data": sample_data,
                "skipped_sheets": skipped_sheets,
                "message": f"Procesados {len(all_records)} registros de {self.total_rows} filas en {sheets_processed} hoja(s)"
            }
        except Exception as e:
            logger.error(f"Error procesando hojas seleccionadas: {e}")
            print(f"Error general procesando hojas seleccionadas: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_rows": 0,
                "processed_rows": 0,
                "sheets_processed": 0,
                "columns_detected": {},
                "sample_data": [],
                "skipped_sheets": []
            }

    def process_any_excel(self, file_content: bytes, filename: str, db: Session, selected_sheets: List[str] = None) -> Dict[str, Any]:
        """Procesa el archivo Excel, SOLO las hojas seleccionadas por el usuario"""
        try:
            print(f"INICIANDO PROCESAMIENTO")
            print(f"Archivo: {filename}")
            print(f"Hojas seleccionadas: {selected_sheets}")

            # Si se especifican hojas seleccionadas, usar el método selectivo
            if selected_sheets:
                return self.process_selected_sheets(file_content, filename, db, selected_sheets)
            
            # Si no se especifican hojas, procesar todas las no vacías (comportamiento original)
            validation = self.validate_excel_file(file_content, filename)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "total_rows": 0,
                    "processed_rows": 0,
                    "sheets_processed": 0,
                    "columns_detected": {},
                    "sample_data": []
                }
            
            # Usar solo las hojas no vacías por defecto
            selected_sheets = validation.get("non_empty_sheets", [])
            print(f"No se especificaron hojas, usando hojas no vacías: {selected_sheets}")
            
            if not selected_sheets:
                return {
                    "success": False,
                    "error": "No hay hojas con datos para procesar",
                    "total_rows": 0,
                    "processed_rows": 0,
                    "sheets_processed": 0,
                    "columns_detected": {},
                    "sample_data": [],
                    "blank_sheets": validation.get("empty_sheets", [])
                }
            
            return self.process_selected_sheets(file_content, filename, db, selected_sheets)
            
        except Exception as e:
            print(f" Error general procesando archivo: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_rows": 0,
                "processed_rows": 0,
                "sheets_processed": 0,
                "columns_detected": {},
                "sample_data": []
            }
    
    def get_progress(self) -> int:
        return self.progress

# Instancia global
upload_processor = DynamicExcelProcessor()