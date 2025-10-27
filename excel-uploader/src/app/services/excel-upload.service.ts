import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ValidationResult, UploadResponse } from '../models/excel-file';

@Injectable({
  providedIn: 'root'
})
export class ExcelUploadService {
  private apiUrl = 'http://localhost:8001'; // Ajusta esto a la URL de tu backend

  constructor(private http: HttpClient) { }

  validateFile(file: File): Observable<ValidationResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ValidationResult>(`${this.apiUrl}/validate/`, formData);
  }

  uploadFile(file: File, selectedSheets: string[], editedData?: any): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('selected_sheets', JSON.stringify(selectedSheets));
    if (editedData) {
      formData.append('edited_data', JSON.stringify(editedData));
    }
    return this.http.post<UploadResponse>(`${this.apiUrl}/upload/`, formData);
  }

  previewSheet(file: File, sheetName: string, maxRows: number = 5): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('sheet_name', sheetName);
    formData.append('max_rows', maxRows.toString());
    return this.http.post(`${this.apiUrl}/preview-sheet/`, formData);
  }

  getDataStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/data-stats/`);
  }
}