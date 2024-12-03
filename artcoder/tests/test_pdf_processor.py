# tests/test_pdf_processor.py

import pytest
from artcoder.pdf_processor import PDFProcessor
import os

@pytest.fixture
def pdf_processor():
    return PDFProcessor()

@pytest.fixture
def sample_pdf_path():
    # Look for PDF in project root directory
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ART-greeley11.25.2024.pdf')

def test_pdf_exists(sample_pdf_path):
    assert os.path.exists(sample_pdf_path), f"Test PDF not found at {sample_pdf_path}"

def test_extract_patients(pdf_processor, sample_pdf_path):
    patients = pdf_processor.extract_patients(sample_pdf_path)
    assert isinstance(patients, list)
    
    if patients:  # If we found any patients
        first_patient = patients[0]
        assert isinstance(first_patient, dict)
        assert all(key in first_patient for key in ['name', 'time', 'type', 'provider', 'dob', 'phone'])

def test_schedule_date(pdf_processor, sample_pdf_path):
    pdf_processor.extract_patients(sample_pdf_path)  # Need to extract first to get date
    date = pdf_processor.get_schedule_date()
    assert date is not None
    assert isinstance(date, str)
