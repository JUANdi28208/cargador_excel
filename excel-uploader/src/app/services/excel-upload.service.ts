import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ValidationResult, UploadResponse } from '../models/excel-file';

@Injectable({
  providedIn: 'root'
})
export class ExcelUploadService {
  private apiUrl = 'http://localhost:8000'; // Ajusta esto a la URL de tu backend

  constructor(private http: HttpClient) { }

  validateFile(file: File): Observable<ValidationResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ValidationResult>(`${this.apiUrl}/validate/`, formData);
  }

  uploadFile(file: File, selectedSheets: string[]): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('selected_sheets', selectedSheets.join(','));
    return this.http.post<UploadResponse>(`${this.apiUrl}/upload/`, formData);
  }
}