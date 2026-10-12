import urllib.parse
from typing import List, Dict
from playwright.sync_api import Page
from app.config import SearchPreferences

class JobSearchEngine:
    def __init__(self, preferences: SearchPreferences):
        self.pref = preferences

    def build_search_url(self, role: str, location: str, page_num: int = 1) -> str:
        formatted_role = role.strip().lower().replace(" ", "-")
        formatted_loc = location.strip().lower().replace(" ", "-").replace("/", "")
        
        # e.g., https://www.naukri.com/full-stack-developer-jobs-in-delhi-ncr?experience=3
        base_url = f"https://www.naukri.com/{formatted_role}-jobs-in-{formatted_loc}"
        if page_num > 1:
            base_url = f"https://www.naukri.com/{formatted_role}-jobs-in-{formatted_loc}-{page_num}"
        
        query_params = {
            "experience": self.pref.min_experience_years
        }
        return f"{base_url}?{urllib.parse.urlencode(query_params)}"

    def extract_job_cards(self, page: Page) -> List[Dict]:
        """Parses job listings on the current Naukri page."""
        job_cards = []
        
        # Select all job tuple wrappers on Naukri
        cards = page.query_selector_all("div.srp-jobtuple-wrapper, div.jobTuple, article.jobTuple")
        for card in cards:
            try:
                title_elem = card.query_selector("a.title")
                company_elem = card.query_selector("a.comp-name, a.companyName")
                exp_elem = card.query_selector("span.expwdth, span.experience")
                loc_elem = card.query_selector("span.locWdth, span.location")
                
                if not title_elem:
                    continue
                
                title = title_elem.inner_text().strip()
                job_url = title_elem.get_attribute("href") or ""
                job_id = card.get_attribute("data-job-id") or job_url.split("-")[-1]
                
                company = company_elem.inner_text().strip() if company_elem else "Unknown Company"
                location = loc_elem.inner_text().strip() if loc_elem else "Unknown"
                experience = exp_elem.inner_text().strip() if exp_elem else ""
                
                # Check if it has an apply button or apply type
                apply_btn = card.query_selector("button.apply-button, span.apply, .apply")
                
                job_cards.append({
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "job_url": job_url,
                    "element": card
                })
            except Exception as e:
                continue
        return job_cards

    def search_jobs(self, page: Page, role: str, location: str, max_pages: int = 2) -> List[Dict]:
        """Navigates to search results pages and extracts job cards."""
        all_jobs = []
        for p in range(1, max_pages + 1):
            url = self.build_search_url(role, location, page_num=p)
            try:
                page.goto(url, wait_until="load", timeout=45000)
                from app.browser import human_delay
                human_delay(2.5, 4.0)
                page.evaluate("() => window.scrollBy(0, 1000)")
                human_delay(1.5, 2.5)
                cards = self.extract_job_cards(page)
                if not cards:
                    break
                all_jobs.extend(cards)
            except Exception as e:
                break
        return all_jobs
