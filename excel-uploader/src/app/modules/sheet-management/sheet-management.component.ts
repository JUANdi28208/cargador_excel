import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ExcelUploadService } from '../../services/excel-upload.service';
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
  
  constructor(
    private router: Router,
    private excelUploadService: ExcelUploadService
  ) { }

  ngOnInit() {
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras.state) {
      this.validationResult = navigation.extras.state['validationResult'];
      this.selectedFile = navigation.extras.state['file'];
      if (this.validationResult?.non_empty_sheets) {
        this.validationResult.non_empty_sheets.forEach(sheet => {
          this.selectedSheets[sheet] = true;
        });
      }
    }
  }

  uploadSelectedSheets(): void {
    if (!this.selectedFile) return;

    const sheetsToUpload = Object.keys(this.selectedSheets).filter(sheet => this.selectedSheets[sheet]);

    this.excelUploadService.uploadFile(this.selectedFile, sheetsToUpload).subscribe(
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
}
