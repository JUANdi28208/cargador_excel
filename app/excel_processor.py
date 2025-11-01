import pandas as pd
from sqlalchemy.orm import Session
import models
import schemas
import io
from typing import Dict, Any, List
import logging
from sqlalchemy import func, desc

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

            print(f" Procesando {len(selected_sheets)} hojas seleccionadas...")

            for sheet_name in selected_sheets:
                try:
                    print(f"   Leyendo hoja: {sheet_name}")
                    
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)

                    # Verificar si la hoja está vacía
                    if self.is_sheet_empty(df):
                        skipped_sheets.append(sheet_name)
                        print(f"    Hoja vacía omitida: {sheet_name}")
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

            print(f" RESUMEN FINAL:")
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
    
    def get_data_stats(self, db: Session) -> Dict[str, Any]:
        """Obtener estadísticas de los datos cargados en la base de datos - VERSIÓN CORREGIDA"""
        try:
            from . import models
            
            # Total de registros
            total_records = db.query(models.ExcelData).count()
            
            # Estadísticas por archivo
            files_stats = db.query(
                models.ExcelData.filename,
                func.count(models.ExcelData.id).label('record_count'),
                func.max(models.ExcelData.upload_date).label('last_upload')
            ).group_by(models.ExcelData.filename).all()
            
            # Total de hojas diferentes
            total_sheets = db.query(models.ExcelData.sheet_name).distinct().count()
            
            # **CORRECCIÓN: Últimos archivos procesados (sin el problema de MySQL)**
            recent_files_subquery = db.query(
                models.ExcelData.filename,
                func.max(models.ExcelData.upload_date).label('max_date')
            ).group_by(models.ExcelData.filename).subquery()
            
            recent_files = db.query(recent_files_subquery.c.filename).order_by(
                desc(recent_files_subquery.c.max_date)
            ).limit(5).all()
            
            # Estadísticas por hoja
            sheets_stats = db.query(
                models.ExcelData.sheet_name,
                func.count(models.ExcelData.id).label('record_count')
            ).group_by(models.ExcelData.sheet_name).all()
            
            # Estadísticas por tipo de archivo (extensión)
            file_extensions = db.query(
                func.substring_index(models.ExcelData.filename, '.', -1).label('extension'),
                func.count(models.ExcelData.id).label('record_count')
            ).group_by('extension').all()
            
            return {
                "total_records": total_records,
                "files_processed": len(files_stats),
                "total_sheets": total_sheets,
                "files_stats": [
                    {
                        "filename": stat.filename, 
                        "record_count": stat.record_count,
                        "last_upload": stat.last_upload.isoformat() if stat.last_upload else None
                    } 
                    for stat in files_stats
                ],
                "sheets_stats": [
                    {
                        "sheet_name": stat.sheet_name,
                        "record_count": stat.record_count
                    }
                    for stat in sheets_stats
                ],
                "file_extensions": [
                    {
                        "extension": stat.extension,
                        "record_count": stat.record_count
                    }
                    for stat in file_extensions
                ],
                "recent_files": [file[0] for file in recent_files],
                "summary": {
                    "total_files": len(files_stats),
                    "total_sheets": total_sheets,
                    "total_records": total_records,
                    "avg_records_per_file": round(total_records / len(files_stats), 2) if files_stats else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando estadísticas: {str(e)}")
            return {
                "error": f"Error generando estadísticas: {str(e)}",
                "total_records": 0,
                "files_processed": 0,
                "total_sheets": 0,
                "files_stats": [],
                "sheets_stats": [],
                "recent_files": [],
                "file_extensions": [],
                "summary": {
                    "total_files": 0,
                    "total_sheets": 0,
                    "total_records": 0,
                    "avg_records_per_file": 0
                }
            }

    def get_chart_data(self, db: Session, filename: str, x_axis: str, y_axis: str, 
                      chart_type: str = "bar", group_by: str = None) -> Dict[str, Any]:
        """Obtener datos formateados para gráficos"""
        try:
            records = db.query(models.ExcelData).filter(
                models.ExcelData.filename == filename
            ).all()
            
            if not records:
                return {
                    "success": False,
                    "error": "No se encontraron datos para este archivo",
                    "data": []
                }
            
            # Procesar datos según el tipo de gráfico
            if chart_type in ["bar", "line"]:
                data = self._process_bar_line_data(records, x_axis, y_axis, group_by)
            elif chart_type == "pie":
                data = self._process_pie_data(records, x_axis, y_axis)
            elif chart_type == "scatter":
                data = self._process_scatter_data(records, x_axis, y_axis, group_by)
            else:
                return {
                    "success": False,
                    "error": "Tipo de gráfico no soportado",
                    "data": []
                }
            
            return {
                "success": True,
                "filename": filename,
                "chart_type": chart_type,
                "x_axis": x_axis,
                "y_axis": y_axis,
                "group_by": group_by,
                "data": data,
                "total_records": len(records)
            }
            
        except Exception as e:
            logger.error(f"Error generando datos de gráfico: {str(e)}")
            return {
                "success": False,
                "error": f"Error generando gráfico: {str(e)}",
                "data": []
            }

    def get_available_columns(self, db: Session, filename: str) -> Dict[str, Any]:
        """Obtener columnas disponibles para análisis y gráficos"""
        try:
            records = db.query(models.ExcelData).filter(
                models.ExcelData.filename == filename
            ).limit(10).all()  # Solo necesitamos algunos registros para analizar
            
            if not records:
                return {
                    "success": False,
                    "error": "No se encontraron datos para este archivo",
                    "columns": []
                }
            
            # Obtener columnas del primer registro
            sample_record = records[0].row_data
            all_columns = list(sample_record.keys())
            
            # Clasificar columnas
            numeric_columns = []
            categorical_columns = []
            date_columns = []
            
            for col in all_columns:
                is_numeric = False
                is_date = False
                
                # Analizar algunos registros para determinar el tipo
                for record in records[:5]:
                    value = record.row_data.get(col)
                    if value:
                        # Verificar si es numérico
                        if self._is_numeric_value(value):
                            is_numeric = True
                            break
                        # Verificar si es fecha (por nombre de columna)
                        elif any(date_keyword in col.lower() for date_keyword in 
                                ['fecha', 'date', 'año', 'year', 'mes', 'month', 'dia', 'day']):
                            is_date = True
                            break
                
                if is_numeric:
                    numeric_columns.append(col)
                elif is_date:
                    date_columns.append(col)
                else:
                    categorical_columns.append(col)
            
            return {
                "success": True,
                "filename": filename,
                "all_columns": all_columns,
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "date_columns": date_columns,
                "sample_record": sample_record
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo columnas disponibles: {str(e)}")
            return {
                "success": False,
                "error": f"Error obteniendo columnas: {str(e)}",
                "columns": []
            }

    def _process_bar_line_data(self, records, x_axis: str, y_axis: str, group_by: str = None) -> List[Dict[str, Any]]:
        """Procesar datos para gráficos de barras y líneas"""
        data_map = {}
        
        for record in records:
            x_value = str(record.row_data.get(x_axis, "N/A"))
            y_value = self._parse_numeric(record.row_data.get(y_axis, 0))
            
            if group_by:
                group_value = str(record.row_data.get(group_by, "General"))
                key = f"{x_value}||{group_value}"
            else:
                key = x_value
                group_value = None
            
            if key not in data_map:
                data_map[key] = {
                    "x": x_value, 
                    "y": 0, 
                    "group": group_value
                }
            
            data_map[key]["y"] += y_value
        
        return list(data_map.values())

    def _process_pie_data(self, records, x_axis: str, y_axis: str) -> List[Dict[str, Any]]:
        """Procesar datos para gráficos de torta"""
        data_map = {}
        
        for record in records:
            category = str(record.row_data.get(x_axis, "N/A"))
            value = self._parse_numeric(record.row_data.get(y_axis, 0))
            
            if category not in data_map:
                data_map[category] = 0
            
            data_map[category] += value
        
        # Filtrar categorías con valor 0 y ordenar por valor descendente
        filtered_data = {k: v for k, v in data_map.items() if v > 0}
        sorted_data = dict(sorted(filtered_data.items(), key=lambda x: x[1], reverse=True))
        
        return [{"name": k, "value": v} for k, v in sorted_data.items()]

    def _process_scatter_data(self, records, x_axis: str, y_axis: str, group_by: str = None) -> List[Dict[str, Any]]:
        """Procesar datos para gráficos de dispersión"""
        data = []
        
        for record in records:
            x_value = self._parse_numeric(record.row_data.get(x_axis, 0))
            y_value = self._parse_numeric(record.row_data.get(y_axis, 0))
            
            # Solo incluir puntos con valores válidos
            if x_value != 0 and y_value != 0:
                point = {
                    "x": x_value,
                    "y": y_value,
                    "group": str(record.row_data.get(group_by, "General")) if group_by else None
                }
                data.append(point)
        
        return data

    def _parse_numeric(self, value) -> float:
        """Convertir valor a numérico de forma segura"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Limpiar caracteres no numéricos
                cleaned = value.replace('$', '').replace(',', '').replace(' ', '').replace('€', '').replace('£', '')
                # Reemplazar puntos decimales si es necesario
                if cleaned.count('.') > 1:
                    parts = cleaned.split('.')
                    cleaned = parts[0] + '.' + ''.join(parts[1:])
                return float(cleaned)
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _is_numeric_value(self, value) -> bool:
        """Determinar si un valor es numérico"""
        try:
            if isinstance(value, (int, float)):
                return True
            elif isinstance(value, str):
                self._parse_numeric(value)
                return True
            else:
                return False
        except:
            return False

# Instancia global
upload_processor = DynamicExcelProcessor()