import re
import json
import os
from typing import Optional, List, Dict
from dotenv import load_dotenv
from app.config import CandidateProfile

load_dotenv()

class ScreeningQAAgent:
    def __init__(self, profile: CandidateProfile):
        self.profile = profile
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.ai_client = None
        
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self.ai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                pass

    def resolve_question(self, question_text: str, options: Optional[List[str]] = None) -> str:
        q_lower = question_text.lower().strip()
        
        # 0. Skip question prompts
        if "skip" in q_lower:
            return "Skip"

        # Filter greetings / instructions
        if "thank you for showing interest" in q_lower or "kindly answer all" in q_lower or "successfully apply" in q_lower:
            return "Yes"

        # 1. Experience in any skill or tool (STRICT NUMERIC ANSWER)
        if any(k in q_lower for k in ["how many years of experience", "years of experience", "experience do you have", "experience in", "experience with"]):
            # Check for specific skill in candidate profile
            for skill, exp in sorted(self.profile.skills_experience.items(), key=lambda x: len(x[0]), reverse=True):
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, q_lower):
                    if options:
                        return self._match_closest_option(f"{exp} years", options, fallback=str(exp))
                    return str(exp)
            
            # If asking for general / total experience
            if any(k in q_lower for k in ["total", "overall", "full"]):
                years = self.profile.total_experience_years
                if options:
                    return self._match_closest_option(f"{years} years", options, fallback=str(years))
                return str(years)

            # Skill not listed in resume -> return 0
            if options:
                return self._match_closest_option("0 years", options, fallback="0")
            return "0"

        # 2. Notice period checks
        if any(k in q_lower for k in ["notice period", "how soon can you join", "serving notice", "lwd", "last working day"]):
            days = self.profile.notice_period_days
            if options:
                return self._match_closest_option(f"{days} days", options, fallback=options[0])
            return str(days)

        # 3. Location / Current Base checks
        if any(k in q_lower for k in ["currently based", "current location", "where are you located", "current city", "living in", "residing in"]):
            loc = self.profile.current_location
            if options:
                return self._match_closest_option(loc, options, fallback=options[0])
            return loc

        # 4. Current & Expected Salary / Compensation together
        if ("current" in q_lower and "expected" in q_lower) or ("compensation" in q_lower and "expectation" in q_lower):
            ans = f"Current CTC: {self.profile.current_ctc_lpa} LPA, Expected CTC: {self.profile.expected_ctc_lpa} LPA"
            if options:
                return self._match_closest_option(f"{self.profile.expected_ctc_lpa} Lakhs", options, fallback=options[0])
            return ans

        # 5. Current CTC checks
        if any(k in q_lower for k in ["current ctc", "current salary", "present ctc", "fixed ctc", "current pkg", "current package"]):
            ctc = self.profile.current_ctc_lpa
            if options:
                return self._match_closest_option(f"{ctc} Lakhs", options, fallback=str(ctc))
            return str(ctc)

        # 6. Expected CTC checks
        if any(k in q_lower for k in ["expected ctc", "expected salary", "salary expectation", "target ctc", "expected package"]):
            ctc = self.profile.expected_ctc_lpa
            if options:
                return self._match_closest_option(f"{ctc} Lakhs", options, fallback=str(ctc))
            return str(ctc)

        # 7. Offer in Hand checks
        if any(k in q_lower for k in ["offer in hand", "holding any offer", "counter offer", "competing offer", "have an offer"]):
            if any(k in q_lower for k in ["ctc", "amount", "package", "value", "lpa", "salary", "how much"]):
                val = self.profile.offer_in_hand_ctc_lpa
                if options:
                    return self._match_closest_option(f"{val} Lakhs", options, fallback=str(val))
                return str(val)
            ans = "Yes" if self.profile.has_offer_in_hand else "No"
            if options:
                return self._match_closest_option(ans, options, fallback="Yes")
            return ans

        # 8. Relocation
        if any(k in q_lower for k in ["relocate", "willing to relocate", "ready to move", "open to relocate"]):
            ans = "Yes" if self.profile.willing_to_relocate else "No"
            if options:
                return self._match_closest_option(ans, options, fallback="Yes")
            return ans

        # 9. Highest Education
        if any(k in q_lower for k in ["highest qualification", "degree", "education", "graduation"]):
            degree = self.profile.highest_education.degree
            if options:
                return self._match_closest_option(degree, options, fallback=options[0])
            return degree

        # 10. Ex-employee / previous employment with recruiter company (e.g. ex-infosys, ex-tcs, former employee)
        if any(k in q_lower for k in ["ex-", "ex ", "former employee", "previous employee", "previously employed", "worked here before", "employee id"]):
            # Check if candidate ever worked at that company
            worked_there = self.profile.current_company.lower() in q_lower
            if not worked_there:
                if "mention na" in q_lower or "write na" in q_lower or "enter na" in q_lower or "if no" in q_lower:
                    return "NA"
                return "No" if not options else self._match_closest_option("No", options, fallback="No")

        # 11. Work from Office (WFO) / Hybrid / Shifts
        if any(k in q_lower for k in ["wfo", "work from office", "5 days wfo", "hybrid", "rotational shift", "night shift", "flexible shift"]):
            ans = "Yes"
            if options:
                return self._match_closest_option(ans, options, fallback="Yes")
            return ans

        # 12. Gender
        if "gender" in q_lower:
            gender = self.profile.gender
            if options:
                return self._match_closest_option(gender, options, fallback=gender)
            return gender

        # 13. Fallback to Gemini Flash for open-ended questions
        if self.ai_client:
            return self._ask_gemini(question_text, options)

        # 14. Rule-based default
        if options and len(options) > 0:
            for opt in options:
                if opt.lower() in ["yes", "immediate", "full time", "b.tech", "30 days", "new delhi", "0", "na"]:
                    return opt
            return options[0]
        return "Yes"

    def _match_closest_option(self, target: str, options: List[str], fallback: str) -> str:
        target_clean = re.sub(r'[^a-zA-Z0-9]', '', target.lower())
        for opt in options:
            opt_clean = re.sub(r'[^a-zA-Z0-9]', '', opt.lower())
            if target_clean in opt_clean or opt_clean in target_clean:
                return opt
        return fallback

    def _ask_gemini(self, question: str, options: Optional[List[str]] = None) -> str:
        try:
            prompt = f"""You are answering an employment screening question on behalf of candidate {self.profile.full_name}.

Candidate Resume Context:
- Current Job: {self.profile.current_job_title} at {self.profile.current_company}
- Total Experience: {self.profile.total_experience_years} years
- Skills & Exp: {json.dumps(self.profile.skills_experience)}
- Location: {self.profile.current_location} (Willing to relocate: {self.profile.willing_to_relocate})
- Compensation: Current CTC {self.profile.current_ctc_lpa} LPA | Expected CTC {self.profile.expected_ctc_lpa} LPA | Offer in Hand {self.profile.offer_in_hand_ctc_lpa} LPA
- Notice Period: {self.profile.notice_period_days} days
- Education: {self.profile.highest_education.degree} in {self.profile.highest_education.field}

Question: "{question}"

Instructions:
- If asking for years of experience or a numeric quantity, output ONLY a single number (e.g. 3.5 or 0).
- If the question asks for past employment at a company he never worked at and asks to write NA, output "NA".
- If asking a Yes/No suitability question (e.g. shifts, WFO, joining), answer "Yes".
- Give ONLY the exact string to type into the input field. Do NOT include markdown, quotes, or explanations.
"""
            if options:
                prompt += f"\nSelect and return ONLY one exact option from: {options}"

            response = self.ai_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            ans = response.text.strip().strip('"').strip("'").strip("`")
            if options and ans not in options:
                return self._match_closest_option(ans, options, options[0])
            return ans
        except Exception:
            return options[0] if options else "Yes"
