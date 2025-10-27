import { Component, ViewChild, ElementRef } from '@angular/core';
import { Router } from '@angular/router';
import { ExcelUploadService } from '../../services/excel-upload.service';
import { UploadStateService } from '../../services/upload-state.service'; // Añade este import
import { ValidationResult } from '../../models/excel-file';

@Component({
  selector: 'app-excel-upload',
  templateUrl: './excel-upload.component.html',
  styleUrls: []
})
export class ExcelUploadComponent {
  @ViewChild('fileInput') fileInput!: ElementRef;
  @ViewChild('uploadArea') uploadArea!: ElementRef;

  selectedFile: File | null = null;
  validationResult: ValidationResult | null = null;
  previewData: any = null;
  
  errorMessage = '';
  showErrorAlert = false;

  constructor(
    private excelUploadService: ExcelUploadService,
    private router: Router,
    private uploadStateService: UploadStateService  // Añade esto
  ) { }

  onFileSelected(event: any): void {
    const files = event.target.files;
    if (files.length > 0) {
      this.handleFiles(files);
    }
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFiles(files);
    }
    this.uploadArea.nativeElement.classList.remove('dragover');
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.uploadArea.nativeElement.classList.add('dragover');
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.uploadArea.nativeElement.classList.remove('dragover');
  }

  handleFiles(files: FileList): void {
    const file = files[0];
    if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
      this.selectedFile = file;
      this.validateFile(file);
    } else {
      this.showError('Por favor, selecciona un archivo Excel válido (.xlsx o .xls)');
    }
  }

  validateFile(file: File): void {
    console.log('Validating file:', file.name);
    this.excelUploadService.validateFile(file).subscribe(
      (result: ValidationResult) => {
        console.log('Validation result received:', result);
        this.validationResult = result;
        if (result.non_empty_sheets && result.non_empty_sheets.length > 0) {
          console.log('Previewing first non-empty sheet:', result.non_empty_sheets[0]);
          this.previewSheet(result.non_empty_sheets[0]);
        }
        this.proceedToSheetManagement();
      },
      (error) => {
        console.error('Error validating file:', error);
        this.showError('Error al validar el archivo: ' + error.message);
      }
    );
  }

  previewSheet(sheetName: string): void {
    console.log('Previewing sheet:', sheetName);
    if (this.selectedFile) {
      this.excelUploadService.previewSheet(this.selectedFile, sheetName).subscribe(
        (result) => {
          console.log('Preview result received:', result);
          this.previewData = result.data;
        },
        (error) => {
          console.error('Error previewing sheet:', error);
          this.showError('Error al previsualizar la hoja: ' + error.message);
        }
      );
    }
  }

  proceedToSheetManagement(): void {
    console.log('Proceeding to sheet management');
    if (this.validationResult && this.selectedFile) {
      // Guarda el estado en el servicio
      this.uploadStateService.setUploadState(
        this.validationResult, 
        this.selectedFile, 
        this.previewData
      );
      
      // Ahora navega sin state
      this.router.navigate(['/sheet-management']).then(() => {
        console.log('Navigation complete');
      }).catch(error => {
        console.error('Navigation error:', error);
      });
    } else {
      console.error('No validation result or file available');
      this.showError('No hay resultados de validación o archivo disponible para continuar');
    }
  }

  showError(message: string): void {
    this.errorMessage = message;
    this.showErrorAlert = true;
  }

  clearFile(): void {
    this.selectedFile = null;
    this.validationResult = null;
    this.previewData = null;
    this.showErrorAlert = false;
    // Limpiar también el estado del servicio
    this.uploadStateService.clearState();
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
  }
}