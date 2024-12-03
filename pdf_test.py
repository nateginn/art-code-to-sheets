# pdf_test.py

from artcoder.pdf_processor import PDFProcessor
import os

def main():
    # Get the absolute path of the PDF in the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, 'ART-greeley11.25.2024.pdf')
    
    processor = PDFProcessor()
    
    print(f"Looking for PDF at: {pdf_path}")
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF file not found at {pdf_path}")
        return
        
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
