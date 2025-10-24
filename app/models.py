from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from .database import Base

class ExcelData(Base):
    __tablename__ = "excel_data"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))  # Nuevo: nombre del archivo
    sheet_name = Column(String(255))  # Nuevo: nombre de la hoja
    row_data = Column(JSON)  # Cambiado: almacena TODOS los datos como JSON
    upload_date = Column(DateTime(timezone=True), server_default=func.now())  # Renombrado
    
    def __repr__(self):
        return f"<ExcelData(filename='{self.filename}', data={self.row_data})>"