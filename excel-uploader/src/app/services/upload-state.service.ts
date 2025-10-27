
import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ValidationResult } from '../models/excel-file';

@Injectable({
  providedIn: 'root'
})
export class UploadStateService {
  private validationResultSource = new BehaviorSubject<ValidationResult | null>(null);
  private selectedFileSource = new BehaviorSubject<File | null>(null);
  private previewDataSource = new BehaviorSubject<any>(null);

  validationResult$ = this.validationResultSource.asObservable();
  selectedFile$ = this.selectedFileSource.asObservable();
  previewData$ = this.previewDataSource.asObservable();

  setUploadState(validationResult: ValidationResult, file: File, previewData: any) {
    this.validationResultSource.next(validationResult);
    this.selectedFileSource.next(file);
    this.previewDataSource.next(previewData);
  }

  getCurrentState() {
    return {
      validationResult: this.validationResultSource.value,
      selectedFile: this.selectedFileSource.value,
      previewData: this.previewDataSource.value
    };
  }

  clearState() {
    this.validationResultSource.next(null);
    this.selectedFileSource.next(null);
    this.previewDataSource.next(null);
  }
}