# tests/test_pdf_extraction.py

from artcoder.pdf_processor import PDFProcessor
import os

def main():
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ART-greeley11.25.2024.pdf')
    processor = PDFProcessor()
    
    # Extract patients
    patients = processor.extract_patients(pdf_path)
    
    # Get schedule date
    print(f"\nSchedule Date: {processor.get_schedule_date()}")
    
    # Print first 3 patients
    print("\nFirst 3 Patient Records:")
    print("-" * 50)
    for i, patient in enumerate(patients[:3]):
        print(f"Patient {i+1}:")
        print(f"Name: {patient['name']}")
        print(f"DOB: {patient['dob']}")
        print(f"Provider: {patient['provider']}")
        print(f"Time: {patient['time']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
