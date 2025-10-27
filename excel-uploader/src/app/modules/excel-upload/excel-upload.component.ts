import { Component, ViewChild, ElementRef } from '@angular/core';
import { Router } from '@angular/router';
import { ExcelUploadService } from '../../services/excel-upload.service';
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
  
  errorMessage = '';
  showErrorAlert = false;

  constructor(
    private excelUploadService: ExcelUploadService,
    private router: Router
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
    this.excelUploadService.validateFile(file).subscribe(
      (result: ValidationResult) => {
        this.validationResult = result;
        // Navegar a la gestión de hojas con los datos de validación
        this.router.navigate(['/sheet-management'], { state: { validationResult: result, file: this.selectedFile } });
      },
      (error) => {
        this.showError('Error al validar el archivo: ' + error.message);
      }
    );
  }

  showError(message: string): void {
    this.errorMessage = message;
    this.showErrorAlert = true;
  }

  clearFile(): void {
    this.selectedFile = null;
    this.validationResult = null;
    this.showErrorAlert = false;
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
  }
}

