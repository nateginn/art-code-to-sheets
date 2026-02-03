# artschedretriever/coder.py

import json
import os
import re
from datetime import datetime
from typing import Dict, List


class CPTCoder:
    def __init__(self):
        self.cpt_patterns = {
            # Time-based therapy patterns with flexible minute matching
            "neuromuscular": r"(?:\b(deep tissue|neuromuscular)\b.*?(\d+)\s*minutes?:?|\b(\d+)\s*minutes?:?.*?\b(deep tissue|neuromuscular)\b)",
            "therapeutic_exercise": r"(?:\b(exercise|exercises)\b.*?(\d+)\s*minutes?:?|\b(\d+)\s*minutes?:?.*?\b(exercise|exercises)\b)",
            "therapeutic_activities": r"(?:\b(therapeutic activities|functional activities)\b\s+.*?(\d+)\s*minutes?:?|\b(\d+)\s*minutes?:?.*?\b(therapeutic activities|functional activities)\b\s*)|(?:\b(therapeutic activities|functional activities)\s*x\s*(\d+)\s*minutes?:?)",
            "ultrasound": r"(?:\b(ultrasound)\b.*?(\d+)\s*minutes?:?|\b(\d+)\s*minutes?:?.*?\b(ultrasound)\b)",
            "electrical_stim": r"(?:\b(electric stim|interferential|TENS)\b.*?(\d+)\s*minutes?:?|\b(\d+)\s*minutes?:?.*?\b(electric stim|interferential|TENS)\b)",
            "active_release": r"(?:\b(active release)\b.*?(\d+)\s*minutes?:?|\b(\d+)\s*minutes?:?.*?\b(active release)\b)",
            "manual_therapy": r"(?:\b(myofascial release|soft tissue|manual therapy)\b.*?(\d+)\s*minutes?:?|\b(\d+)\s*minutes?:?.*?\b(myofascial release|soft tissue|manual therapy)\b)|(?:\b(myofascial release|soft tissue|manual therapy)\s*x\s*(\d+)\s*minutes?:?)",
            "dry_needling": r"\b(dry needling)\b",
            # Manipulation patterns for both spinal and extraspinal
            "manipulation": {
                "spinal": r"Manipulation to the affected (?:spinal segments?): ([^\.]+)",
                "extraspinal": r"Manipulation to the affected (?:extraspinal segments?): ([^\.]+)",
            },
            "chiropractic_adjustment": {
                "spinal": r"(?:Chiropractic adjustment|Chiropractic adjustments) to the affected (?:spinal segments?): ([^\.]+)",
                "extraspinal": r"(?:Chiropractic adjustment|Chiropractic adjustments) to the affected (?:extraspinal segments?): ([^\.]+)",
            },
            # Region-based pattern
            "acupuncture": {
                "main": r"\bAcupuncture\b",
                "regions": r"(?:cervical|thoracic|lumbar|sacral|neck|back)",
            },
            # Exam codes - exact matches only
            "exam": {
                "99203": r"99203(?:-25)?",
                "99204": r"99204(?:-25)?",
                "99205": r"99205(?:-25)?",
                "99213": r"99213(?:-25)?",
                "99214": r"99214(?:-25)?",
                "97162": r"97162",
                "97163": r"97163",
                "97164": r"97164",
            },
            # Generic line pattern: <Procedure> (x|:) <minutes> [CPT]
            # Examples:
            #   "Neuromuscular Re-Education x 25 minutes 97112"
            #   "Therapeutic Activities x 0 minutes"
            #   "Self care and Home Management: 0 minutes 97535"
            #   "Functional Dry Needling x 8 min 20560"
            "generic_time_with_optional_cpt": r"^\s*(?P<proc>Therapeutic Activities|Therapeautic Activities|Neuromuscular\s*Re[-\s]?Education|Therapeutic Exercise|Manual Therapy|Self Care(?: and)? Home Management|(?:Trigger Point|Functional|)\s*Dry\s*Needling)\s*(?:\([^\)]*\)\s*)*(?:x|:)\s*(?P<min>\d+)\s*(?:min|minutes)\b(?:\s*(?P<cpt>\d{5}))?",
            # Alternate order: <Procedure> <CPT> (x|:) <minutes>
            "generic_cpt_before_minutes": r"^\s*(?P<proc>Therapeutic Activities|Therapeautic Activities|Neuromuscular\s*Re[-\s]?Education|Therapeutic Exercise|Manual Therapy|Self Care(?: and)? Home Management|(?:Trigger Point|Functional|)\s*Dry\s*Needling)\s*(?:\([^\)]*\)\s*)*(?P<cpt>\d{5})\s*(?:x|:)\s*(?P<min>\d+)\s*(?:min|minutes)\b",
        }

        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "temp_json"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "coding_test.json")

    def validate_insurance(self, insurance: str) -> str:
        """Standardize insurance types for code selection."""
        insurance = insurance.upper().split(":")[0].split()[0]

        if "MEDICAID" in insurance:
            return "MEDICAID"
        elif "WORK" in insurance or "COMP" in insurance:
            return "WORK"
        elif "AUTO" in insurance:
            return "AUTO"
        elif "SELF" in insurance or "CASH" in insurance:
            return "SELF"
        else:
            return "OMT"  # All other insurance types use OMT codes

    def count_regions(self, text: str, code_type: str = "OMT") -> dict:
        """Count spinal and extraspinal regions."""
        if not text:
            return {"total": 0, "spinal": 0, "extraspinal": False}

        regions = set()
        spinal_regions = set()
        extraspinal = False
        text = text.upper()

        # Handle L/S notation by replacing with "L S" to count them separately
        # Match L/S with optional spaces and commas
        text = re.sub(r"L[\s,]*/[\s,]*S", "L, S", text)
        text = re.sub(r"L[\s,]+S", "L, S", text)

        spinal_patterns = {
            "C": r"\b[C](?:\s|,|/|$)|CERV|NECK",
            "T": r"\b[T](?:\s|,|/|$)|THOR",
            "L": r"\b[L](?:\s|,|/|$)|LUMB",
            "S": r"\b[S](?:\s|,|/|$)|SACR",
        }

        for region, pattern in spinal_patterns.items():
            if re.search(pattern, text):
                regions.add(region)
                spinal_regions.add(region)

        extraspinal_patterns = {
            "SHOULDER": r"SHOULDER",
            "ELBOW": r"ELBOW",
            "WRIST": r"WRIST",
            "HAND": r"HANDS?",
            "HIP": r"HIPS?",
            "KNEE": r"KNEES?",
            "ANKLE": r"ANKLES?",
            "FOOT": r"FEET|FOOT",
            "RIB": r"RIBS?|COSTAL",
            "TMJ": r"TMJ|JAW",
            "SI": r"SI[\s-]?JOINT",
            "CLAVICLE": r"CLAVICLE",
        }

        for region, pattern in extraspinal_patterns.items():
            if re.search(pattern, text):
                regions.add(region)
                extraspinal = True

        return {
            "total": len(regions),
            "spinal": len(spinal_regions),
            "extraspinal": extraspinal,
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
        if insurance_bill == "MEDICAID":
            return "97140"

        if insurance_bill == "OMT":
            total_regions = regions["total"]
            if total_regions <= 2:
                return "98925"
            elif total_regions <= 4:
                return "98926"
            elif total_regions <= 6:
                return "98927"
            elif total_regions <= 8:
                return "98928"
            else:
                return "98929"

        # For CMT (Work Comp, Auto, or Self-Pay)
        spinal_regions = regions["spinal"]
        
        # Check if any spinal manipulation code is in the OMT range (9892x)
        if spinal_regions == 0:
            return None
        elif spinal_regions <= 2:
            spinal_code = "98940"
        elif spinal_regions <= 4:
            spinal_code = "98941"
        else:
            spinal_code = "98942"

        # Prevent using extraspinal manipulation code if spinal codes are OMT
        if spinal_code.startswith("9892"):
            return spinal_code  # Return OMT code only

        # If spinal codes are CMT, allow extraspinal manipulation
        if spinal_regions > 0:
            return spinal_code  # Return CMT code

        return None

    def get_neuromuscular_code(self, insurance_bill: str) -> str:
        """Get neuromuscular CPT code based on insurance."""
        if insurance_bill in ["AUTO", "WORK"]:
            return "97124"
        elif insurance_bill == "SELF":
            return "97124"
        else:
            return "97530"

    def get_therapeutic_activities_code(self, insurance_bill: str) -> str:
        """Get therapeutic activities CPT code."""
        return "97530"  # 97530 is used for all insurance types for therapeutic activities

    def get_time_based_code(
        self, pattern_key: str, insurance_bill: str, plan_text: str
    ) -> Dict:
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
            "ultrasound": "97035",
            "electrical_stim": "97032" if insurance_bill == "MEDICARE" else "97014",
            "active_release": "97140",
            "manual_therapy": "97140",
            "therapeutic_activities": self.get_therapeutic_activities_code(insurance_bill),
        }

        code = code_map.get(pattern_key)
        if not code:
            return None

        return {
            "code": code,
            "units": units,
            "description": f'{pattern_key.replace("_", " ").title()} ({minutes} minutes)',
        }

    def handle_acupuncture(self, plan_text: str) -> List[Dict]:
        """Process acupuncture treatments."""
        if not re.search(
            self.cpt_patterns["acupuncture"]["main"], plan_text, re.IGNORECASE
        ):
            return []

        regions = re.findall(
            self.cpt_patterns["acupuncture"]["regions"], plan_text, re.IGNORECASE
        )
        unique_regions = len(set(regions))

        codes = [{"code": "97810", "units": 1, "description": "Acupuncture Initial"}]
        if unique_regions > 1:
            codes.append(
                {
                    "code": "97811",
                    "units": unique_regions - 1,
                    "description": f"Acupuncture Additional ({unique_regions-1} regions)",
                }
            )
        return codes

    def extract_codes(self, insurance_bill: str, plan_text: str) -> List[Dict]:
        """Extract all CPT codes from plan text."""
        codes = []
        insurance_bill = self.validate_insurance(insurance_bill)

        # Add exam code extraction
        for exam_code, pattern in self.cpt_patterns["exam"].items():
            if re.search(pattern, plan_text):
                codes.append(
                    {"code": exam_code, "units": 1, "description": "Examination"}
                )

        # Helper to merge units for duplicate codes
        def add_or_merge(target_list: List[Dict], code: str, units: int, description: str):
            if units <= 0:
                return
            for item in target_list:
                if item.get("code") == code:
                    item["units"] += units
                    return
            target_list.append({"code": code, "units": units, "description": description})

        # First pass: handle explicit therapist syntax lines with optional CPT at end
        explicit_map = {
            "THERAPEUTIC ACTIVITIES": "97530",
            "NEUROMUSCULAR RE-EDUCATION": "97112",
            "THERAPEUTIC EXERCISE": "97110",
            "MANUAL THERAPY": "97140",
            "SELF CARE HOME MANAGEMENT": "97535",
            "DRY NEEDLING": "20561",
            "TRIGGER POINT DRY NEEDLING": "20561",
            "FUNCTIONAL DRY NEEDLING": "20561",
        }

        explicit_hit = set()
        for pattern_key in ("generic_time_with_optional_cpt", "generic_cpt_before_minutes"):
            for m in re.finditer(self.cpt_patterns[pattern_key], plan_text, re.IGNORECASE | re.MULTILINE):
                proc = m.group("proc").upper().replace("  ", " ").strip()
                minutes = int(m.group("min"))
                explicit_cpt = m.group("cpt")
                units = self.calculate_time_units(minutes)
                if units == 0:
                    continue
                code = explicit_cpt if explicit_cpt else explicit_map.get(proc)
                if code:
                    add_or_merge(codes, code, units, f"{proc.title()} ({minutes} minutes)")
                    # mark section to avoid legacy double-counting
                    if "THERAPEUTIC ACTIVITIES" in proc:
                        explicit_hit.add("therapeutic_activities")
                    elif "NEUROMUSCULAR" in proc:
                        explicit_hit.add("neuromuscular")
                    elif "THERAPEUTIC EXERCISE" in proc:
                        explicit_hit.add("therapeutic_exercise")
                    elif "MANUAL THERAPY" in proc:
                        explicit_hit.add("manual_therapy")
                    elif "HOME MANAGEMENT" in proc:
                        explicit_hit.add("self_care")
                    elif "NEEDLING" in proc:
                        explicit_hit.add("dry_needling")

        # Handle deep tissue/neuromuscular
        match = re.search(self.cpt_patterns["neuromuscular"], plan_text, re.IGNORECASE)
        if match and "neuromuscular" not in explicit_hit:
            if match.group(1):  # Procedure first
                minutes = int(match.group(2))
            elif match.group(3):  # Time first
                minutes = int(match.group(3))
            else:
                minutes = 0

            if minutes > 0:
                units = self.calculate_time_units(minutes)
                if units > 0:
                    # If the matched keyword is neuromuscular, use 97112; if deep tissue, use legacy mapping
                    # Safely pick the keyword group depending on which branch matched
                    keyword_text = (match.group(1) or (match.group(4) if len(match.groups()) >= 4 else "") or "")
                    keyword = keyword_text.lower()
                    if "neuromuscular" in keyword:
                        code = "97112"
                        desc = "Neuromuscular Re-education"
                    elif "deep tissue" in keyword:
                        code = self.get_neuromuscular_code(insurance_bill)
                        desc = "Deep tissue Therapy"
                    else:
                        # Fallback to legacy mapping if keyword is unavailable
                        code = self.get_neuromuscular_code(insurance_bill)
                        desc = "Deep tissue/Neuromuscular"
                    add_or_merge(codes, code, units, f"{desc} ({minutes} minutes)")

        # Handle therapeutic activities
        match = re.search(self.cpt_patterns["therapeutic_activities"], plan_text, re.IGNORECASE)
        if match and "therapeutic_activities" not in explicit_hit:
            if match.group(1):  # Procedure first in standard format
                minutes = int(match.group(2))
            elif match.group(3):  # Time first in standard format
                minutes = int(match.group(3))
            elif match.group(5):  # "x minutes" format
                minutes = int(match.group(6))
            else:
                minutes = 0

            if minutes > 0:
                units = self.calculate_time_units(minutes)
                if units > 0:
                    add_or_merge(
                        codes,
                        self.get_therapeutic_activities_code(insurance_bill),
                        units,
                        f"Therapeutic Activities ({minutes} minutes)",
                    )

        # Handle manipulation
        match = re.search(self.cpt_patterns["manipulation"]["spinal"], plan_text)
        if match:
            regions = self.count_regions(match.group(1))
            manip_code = self.get_manipulation_code(insurance_bill, regions)
            if manip_code:
                add_or_merge(
                    codes,
                    manip_code,
                    1,
                    f"Manipulation ({regions} regions)",
                )

            # Add extraspinal code if needed
            if regions["extraspinal"] and insurance_bill != "MEDICAID":
                # Check if any spinal manipulation code is in the OMT range (9892x)
                if not (manip_code and manip_code.startswith("9892")):
                    add_or_merge(codes, "98943", 1, "Extraspinal Manipulation")

        # Handle therapeutic exercise
        match = re.search(
            self.cpt_patterns["therapeutic_exercise"], plan_text, re.IGNORECASE
        )
        if match and "therapeutic_exercise" not in explicit_hit:
            if match.group(1):  # Procedure first
                minutes = int(match.group(2))
            elif match.group(3):  # Time first
                minutes = int(match.group(3))
            else:
                minutes = 0

            if minutes > 0:
                units = self.calculate_time_units(minutes)
                if units > 0:
                    add_or_merge(codes, "97110", units, f"Therapeutic Exercise ({minutes} minutes)")

        # Handle manual therapy
        match = re.search(self.cpt_patterns["manual_therapy"], plan_text, re.IGNORECASE)
        if match and "manual_therapy" not in explicit_hit:
            if match.group(2):  # Keyword first, standard format
                minutes = int(match.group(2))
            elif match.group(3):  # Time first, standard format
                minutes = int(match.group(3))
            elif match.group(6): # "x minutes" format
                minutes = int(match.group(6))
            else:
                minutes = 0

            if minutes > 0:
                units = self.calculate_time_units(minutes)
                if units > 0:
                    add_or_merge(codes, "97140", units, f"Manual Therapy ({minutes} minutes)")

        # Handle dry needling
        if ("dry_needling" not in explicit_hit) and re.search(self.cpt_patterns["dry_needling"], plan_text, re.IGNORECASE):
            # Simple negation guard: if the note indicates "not today", skip adding dry needling
            if not re.search(r"not\s+today", plan_text, re.IGNORECASE):
                if not any(item.get('code') == '20561' for item in codes):
                    add_or_merge(codes, "20561", 1, "Dry Needling")

        # Process acupuncture
        acupuncture_codes = self.handle_acupuncture(plan_text)
        codes.extend(acupuncture_codes)

        # Add logging if no codes found after processing
        if not codes and plan_text:
            print(f"No CPT codes generated for plan text: {plan_text[:100]}...")

        return codes

    def format_plan_text(self, text: str) -> str:
        """Format plan text into distinct phrases."""
        phrases = re.split(r"(?<=\.)\s*(?=[A-Z])|(?<=\.)(?=[A-Z])", text)
        return "|".join(phrase.strip() for phrase in phrases if phrase.strip())

    def process_plans(self, input_file: str, show_output: bool = True) -> None:
        """Process multiple plans from input file."""
        try:
            with open(input_file, "r") as f:
                data = json.load(f)

            results = []
            for patient in data.get("patients", []):
                plan = patient.get("plan", {})
                insurance = patient.get("insurance", "")

                # Convert plan dict to text format
                plan_text = []
                for section, entries in plan.items():
                    if entries and isinstance(entries, list):
                        plan_text.extend(entries)

                result = {
                    "name": patient.get("name", ""),
                    "insurance": insurance,
                    "plan_text": "\n".join(plan_text),
                    "codes": self.extract_codes(
                        self.validate_insurance(insurance), "\n".join(plan_text)
                    ),
                }
                results.append(result)

            output = {
                "processed_datetime": datetime.now().isoformat(),
                "plans": results,
            }

            with open(self.output_file, "w") as f:
                json.dump(output, f, indent=2)

            if show_output:
                print(f"\nResults saved to: {self.output_file}")

        except Exception as e:
            print(f"Error processing plans: {str(e)}")


class PlanProcessor:
    def __init__(self):
        self.cpt_coder = CPTCoder()
        self.sections = {
            "deep_tissue": r"(?:session of \d+ minutes|deep tissue|neuromuscular)",
            "manipulation": r"Manipulation to the affected (?:spinal segments?|extraspinal segments?)",
            "extraspinal": r"Manipulation to the affected (?:extraspinal segments?|shoulder|elbow|wrist|hands?|hips?|knees?|ankles?|(?:feet|foot)|(?:ribs?|costal)|(?:tmj|jaw)|(?:si[\s-]?joint)|clavicle)",
            "chiropractic_adjustment": r"(?:Chiropractic adjustment|Chiropractic adjustments) to the affected (?:spinal segments?|extraspinal segments?)",
            "therapeutic_exercise": r"Therapeutic exercises|Therex",
            "therapeutic_activities": r"(?:therapeutic activities|functional activities)",
            "acupuncture": r"Acupuncture",
            "ultrasound": r"[Uu]ltrasound",
            "electrical_stim": r"[Ee]lectric\s*stim|[Ii]nterferential|TENS",
            "active_release": r"[Aa]ctive release",
            "manual_therapy": r"[Mm]yofascial release|[Ss]oft tissue|[Mm]anual therapy",
        }

    def process_plan(self, insurance: str, plan_text: str) -> dict:
        """Process plan text and return structured data with CPT codes"""
        procedures = {key: [] for key in self.sections}

        paragraphs = [p.strip() for p in plan_text.split("\n") if p.strip()]

        for para in paragraphs:
            for section, pattern in self.sections.items():
                if re.search(pattern, para, re.IGNORECASE):
                    procedures[section].append(para)

        codes = self.cpt_coder.extract_codes(insurance, plan_text)

        return {"procedures": procedures, "codes": codes}


def main():
    coder = CPTCoder()
    input_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "artcoder",
        "temp_json",
        "agenda_data_GREELEY_20241218.json",
    )
    coder.process_plans(input_file)


if __name__ == "__main__":
    main()
