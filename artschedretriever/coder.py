#artschedretriever/coder.py

import re
import json
import os
from typing import List, Dict
from datetime import datetime

class CPTCoder:
    def __init__(self):
        self.cpt_patterns = {
            'neuromuscular': r'(?:\b(deep tissue|neuromuscular)\b.*?(\d+)\s*minutes?|\b(\d+)\s*minutes?.*?\b(deep tissue|neuromuscular)\b)',
            'manipulation': {
                'regions': r'Manipulation.+?(?:segments?|spine):\s*([^\.]+?)(?:PTR|RTC|\.|$)',
                'region_markers': ['C', 'T', 'L', 'S', 'SI']
            },
            'therapeutic_exercise': r'[Tt]herapeutic exercises?.+?(\d+)\s*minutes?',
            'acupuncture': {
                'main': r'Acupuncture',
                'regions': r'(?:cervical|thoracic|lumbar|sacral|neck|back)'
            },
            'exam': {
                '99213': r'99213-?25|examination.+?15 minutes',
                '99204': r'99204|examination.+?45 minutes'
            }
        }

        
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_json')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, 'coding_test.json')

    def validate_insurance(self, insurance_bill: str) -> str:
        """
        Validate and normalize the insurance field to handle case mismatching.
        Converts known values to standardized uppercase representations.
        """
        if not insurance_bill.strip():
            return "UNKNOWN"
        
        insurance_bill = insurance_bill.strip().upper()
        insurance_map = {
            "AUTO": "AUTO",
            "WORK": "AUTO",
            "WORKERS": "AUTO",
            "WORK COMP": "AUTO",
            "SELF PAY": "SELF PAY",
            "MEDICAID": "MEDICAID",
            "MEDICARE": "MEDICARE"
        }
        
        # Extract first word for cases like "AUTO - HSS LIEN"
        first_word = insurance_bill.split(' - ')[0].split()[0]
        
        # Try mapping first word
        mapped_insurance = insurance_map.get(first_word)
        if mapped_insurance:
            return mapped_insurance
            
        # If no map match, check for AUTO-related keywords
        if any(x in insurance_bill for x in ["AUTO", "LIEN", "HSS"]):
            return "AUTO"
                
        return insurance_bill
            
    def count_regions(self, text: str, code_type: str = 'OMT') -> dict:
        """Count regions based on code type (OMT/CMT)"""
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
        
        # Count spinal regions
        for region, pattern in spinal_patterns.items():
            if re.search(pattern, text):
                regions.add(region)
                spinal_regions.add(region)
        
        # Count extraspinal regions
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

    def get_manipulation_code(self, insurance_bill: str, region_counts: dict, code_type: str = 'OMT') -> str:
        """Determine manipulation CPT code based on insurance, regions, and code type"""
        if not region_counts['total']:
            return None
            
        # Medicaid always gets 97140
        if insurance_bill == "MEDICAID":
            return "97140"
            
        if code_type == 'OMT':
            # OMT coding rules
            total = region_counts['total']
            if insurance_bill in ["AUTO", "SELF PAY"]:
                return "98940" if total <= 2 else "98941"
            else:
                if total <= 2:
                    return "98925"
                elif total <= 4:
                    return "98926"
                elif total <= 6:
                    return "98927"
                elif total <= 8:
                    return "98928"
                else:
                    return "98929"
        
        else:  # CMT
            # CMT spinal coding only
            spinal = region_counts['spinal']
            if spinal <= 2:
                return "98940"
            elif spinal <= 4:
                return "98941"
            else:
                return "98942"

    def get_neuromuscular_code(self, insurance_bill: str) -> str:
        """
        Return the neuromuscular CPT code based on insurance.
        """
        if insurance_bill == "AUTO":
            return "97112"  # Auto and Work Comp use 97112
        elif insurance_bill == "SELF PAY":
            return "97124"  # Self Pay uses 97124
        else:
            return "97530"  # Default code

    def handle_acupuncture(self, plan_text: str) -> List[Dict]:
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
        """
        Extract CPT codes based on the insurance_bill and the plan text.
        """
        codes = []
        print(f"Processing insurance_bill: {insurance_bill}")
        insurance_bill = self.validate_insurance(insurance_bill)
        print(f"Validated insurance_bill: {insurance_bill}")
        
        # Extract E/M codes
        for code, pattern in self.cpt_patterns['exam'].items():
            if re.search(pattern, plan_text, re.IGNORECASE):
                print(f"Matched E/M code: {code} with pattern: {pattern}")
                codes.append({
                    'code': code,
                    'modifier': '25' if '25' in pattern else None,
                    'description': 'E/M'
                })

        # Handle neuromuscular/deep tissue (97530 or 97112)
        time_match = re.search(self.cpt_patterns['neuromuscular'], plan_text, re.IGNORECASE)
        if time_match:
            if time_match.group(1):  # Procedure first
                keyword = time_match.group(1)  # "deep tissue" or "neuromuscular"
                minutes = int(time_match.group(2))  # Time
            elif time_match.group(3):  # Time first
                minutes = int(time_match.group(3))  # Time
                keyword = time_match.group(4)  # "deep tissue" or "neuromuscular"
            else:
                print("No valid groups matched for deep tissue/neuromuscular")
                return codes
            
            print(f"Matched {keyword}: {minutes} minutes")
            units = self.calculate_time_units(minutes)
            print(f"Calculated time units for {minutes} minutes: {units}")
            if units > 0:
                codes.append({
                    'code': self.get_neuromuscular_code(insurance_bill),  # Updated
                    'units': units,
                    'description': f'{keyword.capitalize()} Therapy ({minutes} minutes)'
                })

        # Handle manipulation (97140 or related)
        manip_match = re.search(self.cpt_patterns['manipulation']['regions'], plan_text, re.IGNORECASE)
        if manip_match:
            regions = self.count_regions(manip_match.group(1))
            print(f"Matched manipulation: {regions} regions")
            manip_code = self.get_manipulation_code(insurance_bill, regions)  # Updated
            codes.append({
                'code': manip_code,
                'units': 1,
                'description': f'Manipulation ({regions} regions)'
            })

        # Handle therapeutic exercise
        exercise_match = re.search(self.cpt_patterns['therapeutic_exercise'], plan_text, re.IGNORECASE)
        if exercise_match:
            minutes = int(exercise_match.group(1))
            print(f"Matched therapeutic exercise: {minutes} minutes")
            units = self.calculate_time_units(minutes)
            print(f"Calculated time units for therapeutic exercise: {units}")
            if units > 0:
                codes.append({
                    'code': '97110',
                    'units': units,
                    'description': f'Therapeutic Exercise ({minutes} minutes)'
                })

        # Handle acupuncture
        acupuncture_codes = self.handle_acupuncture(plan_text)
        if acupuncture_codes:
            print(f"Matched acupuncture codes: {acupuncture_codes}")
            codes.extend(acupuncture_codes)

        print(f"Final extracted codes: {codes}")
        return codes



    # Pipes the plan text into distinct treatment phrases
    def format_plan_text(self, text: str) -> str:
        """Split plan text into distinct treatment phrases using pipes"""
        # Split on common treatment boundaries
        phrases = re.split(r'(?<=\.)\s*(?=[A-Z])|(?<=\.)(?=[A-Z])', text)
        # Clean up each phrase and join with pipes
        formatted = '|'.join(phrase.strip() for phrase in phrases if phrase.strip())
        return formatted
    
    def process_plans(self, input_file: str, show_output: bool = True) -> Dict:
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
            'manipulation': r'Manipulation to the affected spinal segments',
            'therapeutic': r'Therapeutic exercises',
            'acupuncture': r'Acupuncture'
        }

    def process_plan(self, insurance: str, plan_text: str) -> dict:
        """Process plan text and return structured data with CPT codes"""
        procedures = {key: [] for key in self.sections}
        
        # Split into paragraphs and process
        paragraphs = [p.strip() for p in plan_text.split('\n') if p.strip()]
        
        for para in paragraphs:
            for section, pattern in self.sections.items():
                if re.search(pattern, para, re.IGNORECASE):
                    procedures[section].append(para)

        # Get CPT codes from processed plan
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
