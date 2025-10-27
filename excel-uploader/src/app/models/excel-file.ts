export interface ExcelFile {
  name: string;
  size: number;
  type: string;
}

export interface ValidationResult {
  valid: boolean;
  error?: string;
  sheets: number;
  total_rows: number;
  sheet_names: string[];
  sheet_info: { [key: string]: any };
  empty_sheets: string[];
  non_empty_sheets: string[];
  has_empty_sheets: boolean;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  total_rows: number;
  processed_rows: number;
  sheets_processed: number;
  columns_detected: { [key: string]: string[] };
  sample_data: any[];
  blank_sheets?: string[];
  skipped_sheets?: string[];
}