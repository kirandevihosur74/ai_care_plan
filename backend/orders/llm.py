from openai import OpenAI
import os
import logging
import re
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger('orders')
_client = None
def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in .env file")
        logger.debug("Initializing OpenAI client")
        _client = OpenAI(api_key=api_key)
    return _client
def clean_care_plan(care_plan: str) -> str:
    conversational_markers = [
        "this care plan is intended to be used",
        "if you want, i will prepare",
        "if you want, i can",
        "if you need, i will",
        "if you need, i can",
        "would you like me to",
        "let me know if you",
        "i can also create",
        "i will also prepare",
    ]
    lines = care_plan.split('\n')
    last_valid_idx = len(lines) - 1
    signature_pattern = r'Date:\s*\d{4}-\d{2}-\d{2}'
    for i, line in enumerate(lines):
        if re.search(signature_pattern, line):
            last_valid_idx = i
    for i in range(last_valid_idx + 1, len(lines)):
        line_lower = lines[i].lower().strip()
        if any(marker in line_lower for marker in conversational_markers):
            logger.debug(f"Removing conversational ending starting at line {i}: {lines[i][:50]}...")
            return '\n'.join(lines[:i]).strip()
    return care_plan.strip()
def generate_care_plan(
    patient_records: str,
    primary_diagnosis: str,
    medication_name: str,
    patient_first_name: str,
    patient_last_name: str,
    patient_mrn: str,
    additional_diagnoses: list[str] = None,
    medication_history: list[str] = None,
) -> str:
    if additional_diagnoses is None:
        additional_diagnoses = []
    if medication_history is None:
        medication_history = []
    prompt = f"""You are an expert clinical pharmacist creating a comprehensive care plan for specialty pharmacy use.
**PATIENT INFORMATION:**
Name: {patient_first_name} {patient_last_name}
MRN: {patient_mrn}
Primary Diagnosis: {primary_diagnosis}
Additional Diagnoses: {', '.join(additional_diagnoses) if additional_diagnoses else 'None'}
Current Medication: {medication_name}
Medication History: {', '.join(medication_history) if medication_history else 'None'}
**CLINICAL RECORDS:**
{patient_records}
**TASK:** Generate a comprehensive pharmacist care plan that meets Medicare documentation requirements and pharma reporting standards.
**REQUIRED FORMAT:**
**START YOUR OUTPUT WITH A PATIENT HEADER:**
```
[Patient First Name] [Patient Last Name] — Comprehensive Pharmacist Care Plan (Specialty Pharmacy)
MRN: [MRN]
DOB: [extract from records if available]  Sex: [extract]  Weight: [extract]
Primary diagnosis: [diagnosis name], [details] — ICD-10: [code]
Additional diagnoses: [list with ICD-10 codes]
Current specialty medication: [medication name and details]
Date of plan: [current date]
Prepared by: Clinical Pharmacist (specialty pharmacy)
```
**THEN INCLUDE THESE NUMBERED SECTIONS:**
**1) PROBLEM LIST / Drug Therapy Problems (DTPs)**
Organize into subsections:
- A. Current therapy-related problems (list all potential adverse effects, infusion reactions, organ toxicity risks)
- B. Drug-drug interactions / contraindications / cautions (evaluate all medications)
- C. Priority safety concerns to address now (immediate risks)
**2) SMART GOALS (Specific, Measurable, Achievable, Relevant, Time-bound)**
Include:
- Clinical goals (with measurable outcomes and timeframes)
- Safety goals (with specific numeric thresholds)
- Quality-of-life / medication use goals (patient education, adherence)
**3) PHARMACIST INTERVENTIONS / PLAN**
Organize into subsections:
- A. Verify and optimize therapy (dosing, product selection, administration strategy, premedication, hydration, prophylaxis)
- B. Monitoring & follow-up interventions (refer to section 4 for schedule)
- C. Patient education (verbal + written) - list specific topics and warning signs
- D. Coordination with providers (communication plan)
**4) MONITORING PLAN & LAB SCHEDULE (specific, actionable)**
Include:
- Baseline (pre-treatment) requirements
- During treatment monitoring (vitals frequency, parameters)
- Laboratory schedule (specific tests and timing: baseline, mid-course, post-course)
- Triggers for escalation / thresholds (numeric criteria for urgent action)
- Follow-up schedule (specific timeframes)
- Contingency / alternative plans (if adverse events occur)
**5) DOCUMENTATION / REPORTING**
Include:
- Product lot number documentation
- Adverse event reporting procedures
- Communication to providers
- Record-keeping requirements
**6) SUMMARY — Clinical impression & plan for this patient**
Provide:
- Clinical summary (brief overview of patient status)
- Expected course and outcomes
- Next steps and follow-up plan
**END THE DOCUMENT WITH:**
```
Provider signature:
[Clinical Pharmacist — Name, Credentials]
Date: [current date in YYYY-MM-DD format]
```
**CRITICAL REQUIREMENTS:**
- Extract patient-specific details (DOB, sex, weight, allergies) from the clinical records
- Use specific numeric values from patient records (lab values, vital signs, doses, weights)
- Include exact timeframes (hours, days, weeks)
- Reference specific drug products and lot numbers when mentioned in records
- Provide measurable thresholds for escalation
- Use appropriate medical terminology
- Make the plan immediately actionable for pharmacy staff
- Ensure Medicare documentation compliance (diagnoses with ICD-10, medications, lot numbers)
**DOCUMENT ENDING RULES:**
- The document MUST end with the provider signature block
- You may include ONE optional "Addendum: Quick-reference escalation thresholds" section after the signature if clinically appropriate
- Do NOT add conversational text after the signature (no "If you want, I will prepare..." or similar)
- Do NOT offer to create additional materials
- This is a final, complete clinical document
Format as a professional clinical document suitable for regulatory review and clinical use."""
    try:
        logger.info(f"Calling OpenAI API - Model: gpt-5-mini, Patient: {patient_first_name} {patient_last_name}, MRN: {patient_mrn}")
        logger.debug(f"Primary Diagnosis: {primary_diagnosis}, Medication: {medication_name}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        client = get_client()
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system", 
                    "content": """You are an expert clinical pharmacist with 15+ years of experience in specialty pharmacy, Medicare Part D documentation, and pharmaceutical reporting.
You create OFFICIAL MEDICAL DOCUMENTATION - not conversational responses.
CRITICAL RULES:
- Generate ONLY the care plan document itself
- Start with patient demographics header
- Include all 6 required sections
- End with provider signature line
- Do NOT add conversational text at the end ("If you want...", "I will prepare...", "Let me know...")
- Do NOT offer to create additional materials after the document
- Do NOT address the reader directly
- Stay in professional clinical documentation mode throughout
- This is a final, complete document ready for regulatory submission and clinical use
Your care plans are detailed, actionable, meet all regulatory standards, and are immediately usable by pharmacy staff."""
                },
                {"role": "user", "content": prompt}
            ]
        )
        care_plan = response.choices[0].message.content
        logger.info(f"OpenAI API call successful - Response length: {len(care_plan)} characters")
        if hasattr(response, 'usage'):
            logger.debug(f"Tokens used - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}")
        care_plan = clean_care_plan(care_plan)
        logger.debug(f"Care plan cleaned - Final length: {len(care_plan)} characters")
        return care_plan
    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to generate care plan: {str(e)}")