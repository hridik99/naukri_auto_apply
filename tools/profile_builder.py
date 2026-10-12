import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROMPT_TEMPLATE = """You are an expert HR and candidate profile parser. 
Extract structured information from the provided resume text and format it STRICTLY as a valid JSON object matching this schema:

{
    "candidate": {
        "full_name": "string",
        "email": "string",
        "phone": "string",
        "current_location": "string",
        "preferred_locations": ["string", "string"],
        "willing_to_relocate": true,
        "total_experience_years": 3.0,
        "current_job_title": "string",
        "current_company": "string",
        "current_ctc_lpa": 12.0,
        "expected_ctc_lpa": 18.0,
        "notice_period_days": 30,
        "highest_education": {
            "degree": "B.Tech",
            "branch": "Computer Science",
            "institution": "University Name",
            "graduation_year": 2023,
            "percentage_or_cgpa": "85%"
        },
        "gender": "Male",
        "skills_experience": {
            "skill_name": 3.0
        },
        "professional_summary": "2-3 concise summary sentences."
    },
    "search_preferences": {
        "roles": ["Relevant Job Title 1", "Relevant Job Title 2"],
        "locations": ["Target City 1", "Remote"],
        "min_experience_years": 1,
        "max_experience_years": 4,
        "max_applications_per_run": 25,
        "skip_company_reviews_under": 3.0,
        "company_blacklist": []
    },
    "bot_settings": {
        "headless": false,
        "slow_mo_ms": 150,
        "min_human_delay_seconds": 2.5,
        "max_human_delay_seconds": 5.0,
        "dry_run": false
    }
}

Resume Text:
---
{resume_text}
---
Output ONLY valid JSON.
"""

def parse_pdf_resume(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def generate_profile_from_text(resume_text: str, output_path: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("[Error] GEMINI_API_KEY is not configured in .env file.")
        print("Please set your free Gemini API key from https://aistudio.google.com/")
        return False

    from google import genai
    client = genai.Client(api_key=api_key)
    
    print("[AI Profile Builder] Analyzing resume with Gemini AI...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=PROMPT_TEMPLATE.replace("{resume_text}", resume_text),
    )
    
    raw = response.text.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    parsed = json.loads(raw)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=4)
    print(f"[Success] Generated new configuration profile saved to: {output_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/profile_builder.py <path_to_resume.pdf or path_to_resume.txt> [output_config.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else "config.json"
    
    if input_file.lower().endswith(".pdf"):
        text = parse_pdf_resume(input_file)
    else:
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()
            
    generate_profile_from_text(text, out_file)
