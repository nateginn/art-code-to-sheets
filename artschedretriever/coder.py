#artschedretriever/coder.py

import re
import json
import os
from typing import List, Dict
from datetime import datetime

class CPTCoder:
    def __init__(self):
        self.cpt_patterns = {
            'neuromuscular': r'(?:deep tissue|neuromuscular).+?(\d+)\s*minutes?',
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

    def validate_insurance(self, insurance: str) -> str:
        if not insurance.strip():
            return "UNKNOWN"
        return insurance.upper().strip()

    def count_regions(self, text: str) -> int:
        if not text:
            return 0
        
        regions = set()
        text = text.upper()
        
        region_patterns = {
            'C': r'\b[C](?:\s|/|$)|CERV|NECK',
            'T': r'\b[T](?:\s|/|$)|THOR',
            'L': r'\b[L](?:\s|/|$)|LUMB',
            'S': r'\b[S](?:\s|/|$)|SACR|SI[\s-]?JOINT'
        }
        
        for region, pattern in region_patterns.items():
            if re.search(pattern, text):
                regions.add(region)
                
        return len(regions)

    def calculate_time_units(self, minutes: int) -> int:
        if minutes < 8:
            return 0
        elif minutes <= 22:
            return 1
        elif minutes <= 37:
            return 2
        elif minutes <= 52:
            return 3
        else:
            return 4

    def get_manipulation_code(self, insurance: str, regions: int) -> str:
        if not regions:
            return None
            
        if insurance == "MEDICAID":
            return "97140"
        elif insurance.startswith("AUTO:") or insurance == "SELF PAY":
            return "98941" if regions > 2 else "98940"
        else:
            return "98926" if regions > 2 else "98925"

    def get_neuromuscular_code(self, insurance: str) -> str:
        if insurance.startswith("AUTO:") or insurance == "SELF PAY":
            return "97112"
        return "97530"

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

    def extract_codes(self, insurance: str, plan_text: str) -> List[Dict]:
        codes = []
        insurance = self.validate_insurance(insurance)
        
        # Extract E/M codes
        for code, pattern in self.cpt_patterns['exam'].items():
            if re.search(pattern, plan_text, re.IGNORECASE):
                codes.append({
                    'code': code,
                    'modifier': '25' if '25' in pattern else None,
                    'description': 'E/M'
                })

        # Handle neuromuscular/deep tissue
        time_match = re.search(self.cpt_patterns['neuromuscular'], plan_text, re.IGNORECASE)
        if time_match:
            minutes = int(time_match.group(1))
            code = self.get_neuromuscular_code(insurance)
            units = self.calculate_time_units(minutes)
            if units > 0:
                codes.append({
                    'code': code,
                    'units': units,
                    'description': f'Neuromuscular ({minutes} minutes)'
                })

        # Handle manipulation
        manip_match = re.search(self.cpt_patterns['manipulation']['regions'], plan_text, re.IGNORECASE)
        if manip_match:
            regions = self.count_regions(manip_match.group(1))
            manip_code = self.get_manipulation_code(insurance, regions)
            if manip_code:
                codes.append({
                    'code': manip_code,
                    'units': 1,
                    'description': f'Manipulation ({regions} regions)'
                })

        # Handle therapeutic exercise
        exercise_match = re.search(self.cpt_patterns['therapeutic_exercise'], plan_text, re.IGNORECASE)
        if exercise_match:
            minutes = int(exercise_match.group(1))
            units = self.calculate_time_units(minutes)
            if units > 0:
                codes.append({
                    'code': '97110',
                    'units': units,
                    'description': f'Therapeutic Exercise ({minutes} minutes)'
                })

        # Handle acupuncture
        codes.extend(self.handle_acupuncture(plan_text))

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

def main():
    coder = CPTCoder()
    input_file = os.path.join(os.path.dirname(__file__), 'plan_sample.txt')
    coder.process_plans(input_file)

if __name__ == "__main__":
    main()
