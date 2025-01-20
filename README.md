# ArtCoder - Medical Practice Management System

A Python-based medical practice management system that automates the extraction and processing of treatment plans and CPT codes from Practice Fusion, synchronizing the data with Google Sheets. This system streamlines the workflow for medical practices, particularly focusing on physical therapy and chiropractic treatments.

## Key Features

- Automated CPT code extraction from treatment plans
- Practice Fusion integration for schedule and patient data
- Google Sheets integration for data management
- Interactive GUI for managing patient schedules and treatment plans
- Support for various medical procedures including:
  - Deep tissue/neuromuscular therapy
  - Spinal and extraspinal manipulations
  - Therapeutic exercises
  - Acupuncture
  - Ultrasound therapy
  - Electrical stimulation
  - Active release therapy
  - Manual therapy

## Requirements

- Python 3.7+
- Google Cloud Platform account with enabled APIs:
  - Google Sheets API
  - Google Drive API
- Practice Fusion account
- Required Python packages (install via Poetry)

## Setup

1. Clone the repository

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Configure credentials:
   - Set up Google Cloud service account and download credentials
   - Save as `service_account.json` in project root
   - Create `.env` file with required environment variables:
     - Practice Fusion credentials
     - Google Drive folder IDs
     - Other configuration settings

## Project Structure

- `artcoder/`
  - `coder.py`: CPT code extraction and processing
  - `config.py`: Configuration management
  - `gui.py`: Main GUI interface
  - `plan.py`: Treatment plan processing
  - `planex.py`: Plan extraction from Practice Fusion
  - `scheduler.py`: Schedule management
  - `sheets_integration.py`: Google Sheets integration
  - `plan_to_sheet.py`: Data synchronization with sheets

## Usage

1. Start the application:
```bash
poetry run python -m artcoder
```

2. Use the GUI to:
   - View and manage patient schedules
   - Process treatment plans
   - Extract CPT codes
   - Sync data with Google Sheets

## Security

- Secure credential management for Practice Fusion and Google services
- Environment-based configuration
- HIPAA compliance considerations in data handling

## Contributing

Please ensure any contributions maintain HIPAA compliance and follow the existing code structure. All new features should include appropriate error handling and logging.
