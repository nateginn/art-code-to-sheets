# artschedretriever/coder.py

import re
import json
import os
from typing import List, Dict
from datetime import datetime

class CPTCoder:
    def __init__(self):
        self.cpt_patterns = {
            # Time-based therapy patterns with flexible minute matching
            'neuromuscular': r'(?:\b(deep tissue|neuromuscular)\b.*?(\d+)\s*minutes?|\b(\d+)\s*minutes?.*?\b(deep tissue|neuromuscular)\b)',
            'therapeutic_exercise': {
                'time': r'(?:Therapeutic exercises?|exercises?) (?:taught and performed )?\(?(\d+) minutes?\)?',
                'regions': r'(?:Therapeutic exercises?|exercises?) (?:taught and performed )?\(?(?:\d+) minutes?\)?(.*?)(?:\.|\n|$)'
            },
            'ultrasound': r'(?:\b(ultrasound)\b.*?(\d+)\s*minutes?|\b(\d+)\s*minutes?.*?\b(ultrasound)\b)',
            'electrical_stim': r'(?:\b(electric stim|interferential|TENS)\b.*?(\d+)\s*minutes?|\b(\d+)\s*minutes?.*?\b(electric stim|interferential|TENS)\b)',
            'active_release': r'(?:\b(active release)\b.*?(\d+)\s*minutes?|\b(\d+)\s*minutes?.*?\b(active release)\b)',
            'manual_therapy': r'(?:\b(myofascial release|soft tissue)\b.*?(\d+)\s*minutes?|\b(\d+)\s*minutes?.*?\b(myofascial release|soft tissue)\b)',
            
            # Manipulation patterns for both spinal and paraspinal
            'manipulation': {
                'spinal': r'Manipulation to the affected (?:spinal|paraspinal) segments?: ([^\.]+)',
                'paraspinal': r'Manipulation to the affected (?:spinal|paraspinal) segments?: ([^\.]+)'
            },
            
            # Region-based pattern
            'acupuncture': {
                'main': r'Acupuncture',
                'regions': r'(?:cervical|thoracic|lumbar|sacral|neck|back)'
            },
            
            # Exam codes - exact matches only
            'exam': {
                '99203': r'99203',
                '99204': r'99204',
                '99205': r'99205',
                '99213': r'99213',
                '99214': r'99214'
            }
        }

        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_json')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, 'coding_test.json')

    def validate_insurance(self, insurance: str) -> str:
        """Standardize insurance types for code selection."""
        insurance = insurance.upper()
        
        if 'MEDICAID' in insurance:
            return 'MEDICAID'
        elif 'WORK' in insurance or 'COMP' in insurance:
            return 'WORK'
        elif 'AUTO' in insurance:
            return 'AUTO'
        elif 'SELF' in insurance or 'CASH' in insurance:
            return 'SELF'
        else:
            return 'OMT'  # All other insurance types use OMT codes

    def count_regions(self, text: str, code_type: str = 'OMT') -> dict:
        """Count spinal and extraspinal regions."""
        if not text:
            return {'total': 0, 'spinal': 0, 'extraspinal': False}
            
        regions = set()
        spinal_regions = set()
        extraspinal = False
        text = text.upper()
        
        # Handle combined L/S notation
        text = text.replace('L/S', 'L S').replace('L,S', 'L S')
        
        spinal_patterns = {
            'C': r'\b[C](?:\s|/|$)|CERV|NECK',
            'T': r'\b[T](?:\s|/|$)|THOR',
            'L': r'\b[L](?:\s|/|$)|LUMB',
            'S': r'\b[S](?:\s|/|$)|SACR'
        }
        
        extraspinal_patterns = {
            'SHOULDER': r'SHOULDER',
            'ELBOW': r'ELBOW',
            'WRIST': r'WRIST',
            'HAND': r'HANDS?',
            'HIP': r'HIPS?',
            'KNEE': r'KNEES?',
            'ANKLE': r'ANKLES?',
            'FOOT': r'FEET|FOOT',
            'RIB': r'RIB|COSTAL',
            'TMJ': r'TMJ|JAW',
            'SI': r'SI[\s-]?JOINT'
        }
        
        for region, pattern in spinal_patterns.items():
            if re.search(pattern, text):
                regions.add(region)
                spinal_regions.add(region)
        
        for region, pattern in extraspinal_patterns.items():
            if re.search(pattern, text):
                regions.add(region)
                extraspinal = True
        
        return {
            'total': len(regions),
            'spinal': len(spinal_regions),
            'extraspinal': extraspinal
        }

    def calculate_time_units(self, minutes: int) -> int:
        """Calculate billing units based on time."""
        if minutes < 8:
            return 0
        elif minutes <= 22:
            return 1
        elif minutes <= 37:
            return 2
        elif minutes <= 52:
            return 3
        elif minutes <= 67:
            return 4
        else:
            return 5

    def get_manipulation_code(self, insurance_bill: str, regions: Dict) -> str:
        """Get the appropriate manipulation code based on insurance and regions."""
        if insurance_bill == 'MEDICAID':
            return '97140'
            
        if insurance_bill == 'OMT':
            total_regions = regions['total']
            if total_regions <= 2:
                return '98925'
            elif total_regions <= 4:
                return '98926'
            elif total_regions <= 6:
                return '98927'
            elif total_regions <= 8:
                return '98928'
            else:
                return '98929'
                
        # For CMT (Work Comp, Auto, or Self-Pay)
        spinal_regions = regions['spinal']
        if spinal_regions == 0:
            return None
        elif spinal_regions <= 2:
            return '98940'
        elif spinal_regions <= 4:
            return '98941'
        else:
            return '98942'

    def get_neuromuscular_code(self, insurance_bill: str) -> str:
        """Get neuromuscular CPT code based on insurance."""
        if insurance_bill in ["AUTO", "WORK COMP"]:
            return "97112"
        elif insurance_bill == "SELF PAY":
            return "97124"
        else:
            return "97530"

    def get_time_based_code(self, pattern_key: str, insurance_bill: str, plan_text: str) -> Dict:
        """Extract time-based therapy codes."""
        match = re.search(self.cpt_patterns[pattern_key], plan_text, re.IGNORECASE)
        if not match:
            return None
            
        if match.group(1):  # Procedure first
            minutes = int(match.group(2))
        elif match.group(3):  # Time first
            minutes = int(match.group(3))
        else:
            return None
            
        units = self.calculate_time_units(minutes)
        if units == 0:
            return None
            
        # Determine code based on pattern
        code_map = {
            'ultrasound': '97035',
            'electrical_stim': '97032' if insurance_bill == 'MEDICARE' else '97014',
            'active_release': '97140',
            'manual_therapy': '97140'
        }
        
        code = code_map.get(pattern_key)
        if not code:
            return None
            
        return {
            'code': code,
            'units': units,
            'description': f'{pattern_key.replace("_", " ").title()} ({minutes} minutes)'
        }

    def handle_acupuncture(self, plan_text: str) -> List[Dict]:
        """Process acupuncture treatments."""
        if not re.search(self.cpt_patterns['acupuncture']['main'], plan_text, re.IGNORECASE):
            return []
            
        regions = re.findall(self.cpt_patterns['acupuncture']['regions'], plan_text, re.IGNORECASE)
        unique_regions = len(set(regions))
        
        codes = [{'code': '97810', 'units': 1, 'description': 'Acupuncture Initial'}]
        if unique_regions > 1:
            codes.append({
                'code': '97811', 
                'units': unique_regions - 1, 
                'description': f'Acupuncture Additional ({unique_regions-1} regions)'
            })
        return codes

    def extract_codes(self, insurance_bill: str, plan_text: str) -> List[Dict]:
        """Extract all CPT codes from plan text."""
        codes = []
        insurance_bill = self.validate_insurance(insurance_bill)
        
        # Extract E/M codes
        for code, pattern in self.cpt_patterns['exam'].items():
            if re.search(pattern, plan_text, re.IGNORECASE):
                codes.append({
                    'code': code,
                    'modifier': '25',  # Always add -25 modifier for E/M codes
                    'description': 'E/M with Modifier 25'  # Updated description to remind about modifier
                })

        # Process manipulation (combine spinal and paraspinal findings)
        all_regions = {'total': 0, 'spinal': 0, 'extraspinal': False}
        
        # Find manipulation text
        manip_text = None
        for manip_type in ['spinal', 'paraspinal']:
            pattern = self.cpt_patterns['manipulation'][manip_type]
            match = re.search(pattern, plan_text, re.IGNORECASE)
            if match:
                manip_text = match.group(0)  # Store the full manipulation text
                regions = self.count_regions(match.group(1))
                all_regions['total'] = max(all_regions['total'], regions['total'])
                all_regions['spinal'] = max(all_regions['spinal'], regions['spinal'])
                all_regions['extraspinal'] = all_regions['extraspinal'] or regions['extraspinal']
        
        # Only check for extraspinal in manipulation text if it exists
        if manip_text:
            extraspinal_pattern = r'(?:extremities|arm|leg|ankle|foot|hand|wrist|knee|shoulder)'
            if re.search(extraspinal_pattern, manip_text, re.IGNORECASE):
                all_regions['extraspinal'] = True
            else:
                all_regions['extraspinal'] = False
        
        # Handle main manipulation code
        if all_regions['total'] > 0:
            manip_code = self.get_manipulation_code(insurance_bill, all_regions)
            if manip_code:
                codes.append({
                    'code': manip_code,
                    'units': 1,
                    'description': f'Manipulation ({str(all_regions)} regions)'
                })
                
            # Handle extraspinal manipulation separately
            if all_regions['extraspinal'] and insurance_bill != 'MEDICAID' and insurance_bill != 'OMT':
                codes.append({
                    'code': '98943',
                    'units': 1,
                    'description': 'Extraspinal Manipulation'
                })

        # Process therapeutic exercises
        time_pattern = self.cpt_patterns['therapeutic_exercise']['time']
        time_match = re.search(time_pattern, plan_text, re.IGNORECASE)
        if time_match:
            minutes = int(time_match.group(1))
            units = max(1, minutes // 15)  # 1 unit per 15 minutes, minimum 1 unit
            codes.append({
                'code': '97110',
                'units': units,
                'description': f'Therapeutic Exercise ({minutes} minutes)'
            })

        # Process time-based treatments
        time_patterns = ['neuromuscular', 'ultrasound', 
                        'electrical_stim', 'active_release', 'manual_therapy']
                        
        for pattern in time_patterns:
            if pattern == 'neuromuscular':
                # Handle neuromuscular separately due to special insurance rules
                match = re.search(self.cpt_patterns[pattern], plan_text, re.IGNORECASE)
                if match:
                    if match.group(1):
                        keyword = match.group(1)
                        minutes = int(match.group(2))
                    elif match.group(3):
                        minutes = int(match.group(3))
                        keyword = match.group(4)
                    else:
                        continue
                        
                    units = self.calculate_time_units(minutes)
                    if units > 0:
                        codes.append({
                            'code': self.get_neuromuscular_code(insurance_bill),
                            'units': units,
                            'description': f'{keyword.capitalize()} Therapy ({minutes} minutes)'
                        })
            else:
                # Handle other time-based treatments
                code_info = self.get_time_based_code(pattern, insurance_bill, plan_text)
                if code_info:
                    codes.append(code_info)

        # Process acupuncture
        acupuncture_codes = self.handle_acupuncture(plan_text)
        codes.extend(acupuncture_codes)

        return codes

    def format_plan_text(self, text: str) -> str:
        """Format plan text into distinct phrases."""
        phrases = re.split(r'(?<=\.)\s*(?=[A-Z])|(?<=\.)(?=[A-Z])', text)
        return '|'.join(phrase.strip() for phrase in phrases if phrase.strip())
    
    def process_plans(self, input_file: str, show_output: bool = True) -> Dict:
        """Process multiple plans from input file."""
        results = {
            'processed_datetime': datetime.now().isoformat(),
            'plans': []
        }

        with open(input_file, 'r') as f:
            for i, line in enumerate(f, 1):
                if '|' not in line:
                    continue
                    
                insurance, plan_text = line.strip().split('|', 1)
                insurance = self.validate_insurance(insurance)
                plan_text = self.format_plan_text(plan_text)
                codes = self.extract_codes(insurance, plan_text)
                
                plan_result = {
                    'plan_number': i,
                    'insurance': insurance,
                    'plan_text': plan_text,
                    'codes': codes
                }
                
                results['plans'].append(plan_result)
                
                if show_output:
                    print(f"\nPlan {i} - Insurance: {insurance}")
                    print("Codes:")
                    for code in codes:
                        if 'modifier' in code:
                            print(f"  {code['code']}-{code['modifier']} ({code['description']})")
                        else:
                            print(f"  {code['code']} units: {code['units']} ({code['description']})")
                    print("-" * 80)

        with open(self.output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        if show_output:
            print(f"\nResults saved to: {self.output_file}")
            
        return results
    
class PlanProcessor:
    def __init__(self):
        self.cpt_coder = CPTCoder()
        self.sections = {
            'deep_tissue': r'(?:session of \d+ minutes|deep tissue|neuromuscular)',
            'manipulation': r'Manipulation to the affected (?:spinal segments|paraspinal segments)',
            'extraspinal': r'Manipulation to the affected (?:extremities|arm|leg|ankle|foot|hand|wrist|knee|shoulder)',
            'therapeutic': r'Therapeutic exercises',
            'acupuncture': r'Acupuncture',
            'ultrasound': r'[Uu]ltrasound',
            'electrical_stim': r'[Ee]lectric\s*stim|[Ii]nterferential|TENS',
            'active_release': r'[Aa]ctive release',
            'manual_therapy': r'[Mm]yofascial release|[Ss]oft tissue'
        }

    def process_plan(self, insurance: str, plan_text: str) -> dict:
        """Process plan text and return structured data with CPT codes"""
        procedures = {key: [] for key in self.sections}
        
        paragraphs = [p.strip() for p in plan_text.split('\n') if p.strip()]
        
        for para in paragraphs:
            for section, pattern in self.sections.items():
                if re.search(pattern, para, re.IGNORECASE):
                    procedures[section].append(para)

        codes = self.cpt_coder.extract_codes(insurance, plan_text)
        
        return {
            'procedures': procedures,
            'codes': codes
        }

def main():
    coder = CPTCoder()
    input_file = os.path.join(os.path.dirname(__file__), 'plan_sample.txt')
    coder.process_plans(input_file)

if __name__ == "__main__":
    main()