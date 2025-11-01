from sqlalchemy.orm import Session
from app.models.database import ProcessedData
from app.schemas.excel_schemas import ChartData, ChartResponse
from sqlalchemy import func

class ChartService:
    
    @staticmethod
    def generate_charts(db: Session, upload_id: int) -> ChartResponse:
        """
        Genera datos para los gráficos basados en los datos procesados
        """
        # Obtener datos para el gráfico de barras (trading chart)
        trading_data = db.query(
            ProcessedData.column_name,
            func.avg(ProcessedData.value).label('avg_value')
        ).filter(
            ProcessedData.upload_id == upload_id
        ).group_by(
            ProcessedData.column_name
        ).all()
        
        # Obtener datos para el gráfico de pie
        pie_data = db.query(
            ProcessedData.category,
            func.count(ProcessedData.id).label('count')
        ).filter(
            ProcessedData.upload_id == upload_id
        ).group_by(
            ProcessedData.category
        ).all()
        
        # Preparar datos para el gráfico de trading (barras)
        trading_labels = [item.column_name for item in trading_data]
        trading_values = [float(item.avg_value) for item in trading_data]
        
        trading_chart = ChartData(
            labels=trading_labels,
            datasets=[{
                'label': 'Valores Promedio',
                'data': trading_values,
                'backgroundColor': ['#1976d2', '#388e3c', '#fbc02d', '#d32f2f', '#7b1fa2'],
            }]
        )
        
        # Preparar datos para el gráfico de pie
        pie_labels = [item.category for item in pie_data]
        pie_values = [int(item.count) for item in pie_data]
        
        pie_chart = ChartData(
            labels=pie_labels,
            datasets=[{
                'data': pie_values,
                'backgroundColor': ['#1976d2', '#388e3c', '#fbc02d', '#d32f2f', '#7b1fa2'],
            }]
        )
        
        return ChartResponse(
            trading_chart=trading_chart,
            pie_chart=pie_chart
        )
    
    @staticmethod
    def generate_sample_charts() -> ChartResponse:
        """
        Genera gráficos de ejemplo cuando no hay datos
        """
        trading_chart = ChartData(
            labels=['A', 'B', 'C', 'D'],
            datasets=[{
                'label': 'Valores',
                'data': [100, 80, 120, 60],
                'backgroundColor': ['#1976d2', '#388e3c', '#fbc02d', '#d32f2f'],
            }]
        )
        
        pie_chart = ChartData(
            labels=['A', 'B', 'C', 'D'],
            datasets=[{
                'data': [40, 30, 20, 10],
                'backgroundColor': ['#1976d2', '#388e3c', '#fbc02d', '#d32f2f'],
            }]
        )
        
        return ChartResponse(
            trading_chart=trading_chart,
            pie_chart=pie_chart
        )