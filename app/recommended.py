import time
from typing import List, Dict
from playwright.sync_api import Page
from app.browser import human_delay

class RecommendedJobsEngine:
    def __init__(self):
        self.recommended_url = "https://www.naukri.com/mnjuser/recommendedjobs"
        self.homepage_url = "https://www.naukri.com/mnjuser/homepage"

    def fetch_recommended_jobs(self, page: Page, max_cards: int = 150) -> List[Dict]:
        """Navigates to Naukri recommended jobs and scrolls to harvest all cards."""
        jobs = []
        page.goto(self.recommended_url, timeout=60000)
        human_delay(3, 5)

        # Check if redirected to login
        if "nlogin" in page.url or "login" in page.url:
            print("[Recommended Engine] User session is not logged in. Please run: python run.py --login")
            return []

        # Smooth scrolling to trigger lazy loading of recommended cards
        scroll_attempts = 0
        max_scrolls = 15
        seen_job_ids = set()

        while scroll_attempts < max_scrolls and len(jobs) < max_cards:
            page.evaluate("window.scrollBy(0, 1000)")
            human_delay(1.5, 2.5)

            # Extract job cards on page
            cards = page.query_selector_all("article.jobTuple, div.jobTuple, div.srp-jobtuple-wrapper, div.recommended-job-card, div.tuple")
            for card in cards:
                try:
                    title_elem = card.query_selector("p.title, a.title, .title, [class*='title']")
                    comp_elem = card.query_selector("span.subTitle, a.comp-name, a.companyName, .companyInfo")
                    exp_elem = card.query_selector("li.experience span, span.expwdth, span.experience")
                    loc_elem = card.query_selector("li.location span, span.locWdth, span.location")

                    if not title_elem:
                        continue

                    title = title_elem.inner_text().strip()
                    job_id = card.get_attribute("data-job-id") or ""
                    
                    href = title_elem.get_attribute("href") if title_elem.evaluate("el => el.tagName.toLowerCase() == 'a'") else ""
                    if not job_id and href:
                        job_id = href.split("-")[-1]

                    if not job_id:
                        continue

                    if job_id in seen_job_ids:
                        continue

                    seen_job_ids.add(job_id)
                    job_url = href if (href and "http" in href) else f"https://www.naukri.com/job-listings-{job_id}"
                    
                    company = comp_elem.inner_text().strip() if comp_elem else "Unknown Company"
                    location = loc_elem.inner_text().strip() if loc_elem else "India"
                    exp = exp_elem.inner_text().strip() if exp_elem else ""

                    jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "experience": exp,
                        "job_url": job_url,
                        "source": "RECOMMENDED"
                    })

                    if len(jobs) >= max_cards:
                        break
                except Exception:
                    continue

            scroll_attempts += 1

        # Fallback to homepage matching cluster if recommended page returned 0
        if not jobs:
            jobs = self._fetch_homepage_jobs(page, max_cards)

        return jobs

    def _fetch_homepage_jobs(self, page: Page, max_cards: int = 30) -> List[Dict]:
        """Harvests matched jobs from the user dashboard / homepage."""
        jobs = []
        page.goto(self.homepage_url, timeout=60000)
        human_delay(3, 5)

        cards = page.query_selector_all("div.tuple, div.jobTuple, div.carousel-card, div.card")
        for card in cards:
            try:
                title_elem = card.query_selector("a.title, a.job-title, .title")
                comp_elem = card.query_selector("a.comp-name, a.companyName, .company")
                if not title_elem:
                    continue
                title = title_elem.inner_text().strip()
                job_url = title_elem.get_attribute("href") or ""
                job_id = card.get_attribute("data-job-id") or job_url.split("-")[-1]
                company = comp_elem.inner_text().strip() if comp_elem else "Unknown Company"

                jobs.append({
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "location": "India",
                    "experience": "",
                    "job_url": job_url,
                    "source": "HOMEPAGE_MATCH"
                })
            except Exception:
                continue
        return jobs
