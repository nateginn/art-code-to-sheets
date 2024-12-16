class PlanOrganizer:
    def __init__(self):
        self.plan_sections = {
            'intro': r'Today the patient received:',
            'deep_tissue': r'(?:session of \d+ minutes|deep tissue|neuromuscular)',
            'manipulation': r'Manipulation to the affected spinal segments:',
            'therapeutic': r'Therapeutic exercises taught',
            'followup': r'(?:RTX|PTR|RTC)'
        }

    def organize_plan(self, text):
        result = {
            'intro': None,
            'deep_tissue': None,
            'manipulation': None,
            'therapeutic': None,
            'followup': None
        }
        
        # Assuming text comes in with paragraphs split by newlines
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        for para in paragraphs:
            if para.startswith('Today'):
                result['intro'] = para
            elif 'deep tissue' in para.lower() or 'session of' in para.lower():
                result['deep_tissue'] = para
            elif para.startswith('Manipulation'):
                result['manipulation'] = para
            elif para.startswith('Therapeutic'):
                result['therapeutic'] = para
            elif any(x in para for x in ['RTX', 'PTR', 'RTC']):
                result['followup'] = para
                
        return result

# Example usage:
sample_text = """Today the patient received:

A session of 25 minutes of deep tissue and/or neuromuscular re-education was provided to diminish re-educate injured muscle and fascia, myospasms, and improve circulation for improved healing outcomes.

Manipulation to the affected spinal segments: C, T, L/S

Therapeutic exercises taught and performed (15 minutes) today include: 10 minutes of stationary bike, weight machine extension (3x10), and weight machine flexion (3x10), and leg press 3x10

RTX 1 for one more visit."""

organizer = PlanOrganizer()
structured_plan = organizer.organize_plan(sample_text)

# Result would look like:
"""{
    'intro': 'Today the patient received:',
    'deep_tissue': 'A session of 25 minutes of deep tissue...',
    'manipulation': 'Manipulation to the affected spinal segments: C, T, L/S',
    'therapeutic': 'Therapeutic exercises taught and performed...',
    'followup': 'RTX 1 for one more visit.'
}"""
