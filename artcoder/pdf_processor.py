# artcoder/pdf_processor.py

import tabula
import pandas as pd
import re
from datetime import datetime

class PDFProcessor:
    def __init__(self):
        self.schedule_date = None
    
    def extract_patients(self, pdf_path):
        """Extract patient information from the PDF schedule."""
        try:
            print(f"Reading PDF: {pdf_path}")
            tables = tabula.read_pdf(pdf_path, pages='1', area=[0, 0, 800, 800], guess=False)
            print(f"Found {len(tables)} tables")
            
            if tables and len(tables) > 0:
                for col in tables[0].columns:
                    match = re.search(r'Schedule Standard view - \w+, (\w+ \d{1,2}, \d{4})', str(col))
                    if match:
                        self.schedule_date = match.group(1)
                        break

            patients = []
            if tables and len(tables) > 0:
                main_table = tables[0]
                for idx in range(len(main_table)):
                    row_data = ' '.join(str(val) for val in main_table.iloc[idx] if pd.notna(val))
                    
                    if 'Seen' in row_data and re.search(r'\d{1,2}:\d{2}\s*[AP]M', row_data):
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', row_data)
                        name_match = re.search(r'Seen\s+(.*?)\s+\d{1,2}:\d{2}\s*[AP]M', row_data)
                        type_match = re.search(r'(CHIRO Follow Up|CHIRO New|MASSAGE)', row_data)
                        provider_match = re.search(r'[AP]M\s+([A-Za-z]+(?:\s+[A-Za-z]+)*?)(?:\s+(?:CHIRO Follow Up|CHIRO New|MASSAGE)|$)', row_data)
                        
                        if name_match and time_match:
                            patient = {
                                'name': name_match.group(1).strip(),
                                'time': time_match.group(1),
                                'type': type_match.group(1) if type_match else '',
                                'provider': provider_match.group(1) if provider_match else '',
                                'dob': '',
                                'phone': ''
                            }
                            
                            if idx + 1 < len(main_table):
                                next_row = ' '.join(str(val) for val in main_table.iloc[idx + 1] if pd.notna(val))
                                dob_phone_match = re.search(r'(\d{2}/\d{2}/\d{4})\s+M\.\s+(\(\d{3}\)\s+\d{3}-\d{4})', next_row)
                                if dob_phone_match:
                                    patient['dob'] = dob_phone_match.group(1)
                                    patient['phone'] = dob_phone_match.group(2)
                            
                            patients.append(patient)
            return patients
        
        except Exception as e:
            print(f"Error extracting data from PDF: {str(e)}")
            return []
    
    def get_schedule_date(self):
        """Get the extracted schedule date."""
        if self.schedule_date:
            try:
                try:
                    date_obj = datetime.strptime(self.schedule_date, '%m/%d/%y')
                    return date_obj.strftime('%m/%d/%y')
                except ValueError:
                    pass

                try:
                    date_obj = datetime.strptime(self.schedule_date, '%B %d, %Y')
                    return date_obj.strftime('%m/%d/%y')
                except ValueError:
                    pass
                
            except Exception as e:
                print(f"Error parsing date: {str(e)}")
                
        return datetime.now().strftime('%m/%d/%y')
