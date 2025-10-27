import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { UploadResponse } from '../../models/excel-file';
import { ExcelUploadService } from '../../services/excel-upload.service';
import { Chart } from 'chart.js/auto';

@Component({
  selector: 'app-result-view',
  templateUrl: './result-view.component.html',
  styleUrls: []
})
export class ResultViewComponent implements OnInit {
  uploadResult: UploadResponse | null = null;
  dataStats: any = null;
  chart: Chart | null = null;

  constructor(
    private router: Router,
    private excelUploadService: ExcelUploadService
  ) { }

  ngOnInit() {
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras.state) {
      this.uploadResult = navigation.extras.state['uploadResult'];
    }
    this.loadDataStats();
  }

  ngAfterViewInit() {
    this.createChart();
  }

  loadDataStats() {
    this.excelUploadService.getDataStats().subscribe(
      (stats) => {
        this.dataStats = stats;
        this.createChart();
      },
      (error) => {
        console.error('Error al cargar las estadísticas:', error);
      }
    );
  }

  createChart() {
    if (this.dataStats && !this.chart) {
      const ctx = document.getElementById('statsChart') as HTMLCanvasElement;
      this.chart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['Total de registros', 'Archivos únicos', 'Hojas únicas'],
          datasets: [{
            label: 'Estadísticas de datos',
            data: [this.dataStats.total_records, this.dataStats.unique_files, this.dataStats.unique_sheets],
            backgroundColor: [
              'rgba(255, 99, 132, 0.2)',
              'rgba(54, 162, 235, 0.2)',
              'rgba(255, 206, 86, 0.2)'
            ],
            borderColor: [
              'rgba(255, 99, 132, 1)',
              'rgba(54, 162, 235, 1)',
              'rgba(255, 206, 86, 1)'
            ],
            borderWidth: 1
          }]
        },
        options: {
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      });
    }
  }

  // Métodos para mostrar los resultados
  getObjectKeys(obj: any): string[] {
    return Object.keys(obj);
  }

  getObjectValues(obj: any): any[] {
    return Object.values(obj);
  }
}

