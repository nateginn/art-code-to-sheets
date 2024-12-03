# PDF to Google Sheets Converter

A Python application that extracts patient schedule data from PDF files and uploads it to Google Sheets. Includes both automated PDF processing and manual data entry capabilities.

## Features

- PDF schedule data extraction
- Automated Google Sheets integration
- Manual data entry form
- Configuration management
- Date detection and formatting
- CPT code management

## Requirements

- Python 3.7+
- tabula-py
- pandas
- google-api-python-client
- google-auth
- tkinter

## Setup

1. Install dependencies:
```bash
pip install tabula-py pandas google-api-python-client google-auth
```

2. Configure Google Sheets API:
- Create a Google Cloud project
- Enable Sheets and Drive APIs
- Create service account credentials
- Save credentials as `credentials.json` in project root

## Usage

### Automated PDF Processing
```python
from pdf_to_sheets import PDFProcessor, SheetsManager

processor = PDFProcessor()
patients = processor.extract_patients('schedule.pdf')
```

### Manual Data Entry
```python
from pdf_to_sheets import EntryForm
form = EntryForm(root)  # root is your tkinter root window
```

## Configuration

Default settings in `config.json`:
```json
{
    "credentials_path": "./credentials.json",
    "active_spreadsheet_id": null,
    "spreadsheet_name": "Patient Records"
}
```

## Project Structure

- `config.py`: Configuration management
- `converter.py`: Main PDF to Sheets conversion
- `dialogs.py`: Custom dialog windows
- `form_window.py`: Manual entry form
- `pdf_processor.py`: PDF data extraction
- `sheets_manager.py`: Google Sheets integration
