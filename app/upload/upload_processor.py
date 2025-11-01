from excel_processor import DynamicExcelProcessor, upload_processor

def validate_excel_file(*args, **kwargs):
    return upload_processor.validate_excel_file(*args, **kwargs)

def get_sheet_preview(*args, **kwargs):
    return upload_processor.get_sheet_preview(*args, **kwargs)

def process_any_excel(*args, **kwargs):
    return upload_processor.process_any_excel(*args, **kwargs)

def process_edited_data(*args, **kwargs):
    return upload_processor.process_edited_data(*args, **kwargs)

def get_data_stats(*args, **kwargs):
    return upload_processor.get_data_stats(*args, **kwargs)

def get_progress():
    return upload_processor.get_progress()

def update_progress(progress):
    upload_processor.progress = progress