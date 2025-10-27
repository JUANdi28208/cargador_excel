import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ExcelUploadService } from '../../services/excel-upload.service';
import { UploadStateService } from '../../services/upload-state.service'; // Añade este import
import { ValidationResult, UploadResponse } from '../../models/excel-file';

@Component({
  selector: 'app-sheet-management',
  templateUrl: './sheet-management.component.html',
  styleUrls: []
})
export class SheetManagementComponent implements OnInit {
  validationResult: ValidationResult | null = null;
  selectedFile: File | null = null;
  selectedSheets: { [key: string]: boolean } = {};
  previewData: { [key: string]: any[] } = {};
  editedData: { [sheet: string]: { [key: string]: any }[] } = {};
  
  constructor(
    private router: Router,
    private excelUploadService: ExcelUploadService,
    private uploadStateService: UploadStateService  // Añade esto
  ) { }

  ngOnInit() {
    console.log('SheetManagementComponent initialized');
    
    // Obtener el estado del servicio en lugar del router
    const state = this.uploadStateService.getCurrentState();
    console.log('State from service:', state);
    
    if (state.validationResult && state.selectedFile) {
      this.validationResult = state.validationResult;
      this.selectedFile = state.selectedFile;
      const previewData = state.previewData;
      
      console.log('Received validation result:', this.validationResult);
      console.log('Received file:', this.selectedFile?.name);
      console.log('Received preview data:', previewData);

      if (this.validationResult?.non_empty_sheets) {
        this.validationResult.non_empty_sheets.forEach(sheet => {
          this.selectedSheets[sheet] = true;
          if (previewData && previewData[sheet]) {
            this.previewData[sheet] = previewData[sheet];
            this.editedData[sheet] = [...previewData[sheet]];
          } else {
            this.previewSheet(sheet);
          }
        });
      }
    } else {
      console.error('No state available in UploadStateService');
      
      // También verifica si hay estado en el router por compatibilidad
      const navigation = this.router.getCurrentNavigation();
      if (navigation?.extras?.state) {
        console.log('Found state in navigation, migrating to service...');
        const navState = navigation.extras.state;
        this.uploadStateService.setUploadState(
          navState['validationResult'],
          navState['file'],
          navState['previewData']
        );
        // Recargar el componente o llamar a ngOnInit nuevamente
        this.ngOnInit();
        return;
      }
      
      // Si no hay estado en ningún lado, redirigir
      this.router.navigate(['/']);
    }
  }

  previewSheet(sheetName: string): void {
    console.log('Previewing sheet:', sheetName);
    if (this.selectedFile) {
      this.excelUploadService.previewSheet(this.selectedFile, sheetName).subscribe(
        (result) => {
          this.previewData[sheetName] = result.data;
          this.editedData[sheetName] = [...result.data];
        },
        (error) => {
          console.error('Error al previsualizar la hoja:', error);
        }
      );
    }
  }

  updateEditedData(sheet: string, rowIndex: number, columnName: string, value: any): void {
    if (!this.editedData[sheet]) {
      this.editedData[sheet] = [];
    }
    if (!this.editedData[sheet][rowIndex]) {
      this.editedData[sheet][rowIndex] = {};
    }
    this.editedData[sheet][rowIndex][columnName] = value;
  }

  uploadSelectedSheets(): void {
    if (!this.selectedFile) return;

    const sheetsToUpload = Object.keys(this.selectedSheets).filter(sheet => this.selectedSheets[sheet]);

    this.excelUploadService.uploadFile(this.selectedFile, sheetsToUpload, this.editedData).subscribe(
      (result: UploadResponse) => {
        // Navegar a la vista de resultados
        this.router.navigate(['/result-view'], { state: { uploadResult: result } });
      },
      (error) => {
        console.error('Error al subir el archivo:', error);
        // Manejar el error apropiadamente
      }
    );
  }

  getSelectedSheetsCount(): number {
    return Object.values(this.selectedSheets).filter(Boolean).length;
  }

  getSheetRows(sheet: string): number {
    return this.validationResult?.sheet_info?.[sheet]?.rows ?? 0;
  }

  getEditedDataForSheet(sheet: string, rowIndex: number, columnName: string): any {
    return this.editedData[sheet]?.[rowIndex]?.[columnName] ?? '';
  }

  setEditedDataForSheet(sheet: string, rowIndex: number, columnName: string, value: any): void {
    this.updateEditedData(sheet, rowIndex, columnName, value);
  }

  goBack(): void {
    // Opcional: limpiar el estado si quieres empezar de nuevo
    // this.uploadStateService.clearState();
    this.router.navigate(['/']);
  }
}