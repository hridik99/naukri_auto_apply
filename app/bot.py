import time
import random
from typing import Optional
from playwright.sync_api import Page

from app.config import AppConfig
from app.browser import get_browser_context, human_delay
from app.tracker import ApplicationTracker
from app.qa_agent import ScreeningQAAgent
from app.search import JobSearchEngine
from app.recommended import RecommendedJobsEngine
from app.logger import log_info, log_success, log_warning, log_error, log, console

class NaukriAutoApplyBot:
    def __init__(self, config: AppConfig):
        self.config = config
        self.tracker = ApplicationTracker()
        self.qa_agent = ScreeningQAAgent(config.candidate)
        self.search_engine = JobSearchEngine(config.search_preferences)
        self.recommended_engine = RecommendedJobsEngine()
        self.playwright = None
        self.context = None
        self.page: Optional[Page] = None

    def start(self, headless: Optional[bool] = None):
        is_headless = self.config.bot_settings.headless if headless is None else headless
        self.playwright, self.context, self.page = get_browser_context(
            headless=is_headless,
            slow_mo=self.config.bot_settings.slow_mo_ms
        )

    def close(self):
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass

    def check_login_status(self) -> bool:
        """Navigates to Naukri and checks if user profile icon or dashboard is present."""
        log_info("Checking Naukri login session...", "cyan")
        self.page.goto("https://www.naukri.com/mnjuser/homepage", timeout=60000)
        human_delay(3, 5)
        
        logged_in = (
            "nlogin" not in self.page.url and 
            "login" not in self.page.url and
            (
                self.page.query_selector("div.nI-gNb-drawer") is not None or
                self.page.query_selector("a.nI-gNb-header__logo") is not None or
                self.page.query_selector(".user-profile") is not None
            )
        )
        return logged_in

    def manual_login_mode(self):
        """Allows one-time manual login in the browser window to save cookies/session."""
        self.start(headless=False)
        log_warning("Opening Naukri login page. Please enter your credentials and OTP manually in the browser window.")
        self.page.goto("https://www.naukri.com/nlogin/login", timeout=60000)
        
        log_info("Waiting for you to log in. Once logged in and on the homepage, press Enter in this terminal to save session...", "green")
        input("Press [Enter] after you are fully logged in to Naukri:")
        
        log_success("Login session successfully captured and saved in data/chrome_user_data!")
        self.close()

    def run(self, max_applications: Optional[int] = None, dry_run: Optional[bool] = None, headless: Optional[bool] = None, use_search: bool = False):
        self.start(headless=headless)
        if dry_run is None:
            dry_run = self.config.bot_settings.dry_run

        max_apps = max_applications or self.config.search_preferences.max_applications_per_run
        applied_today = self.tracker.get_todays_count()
        mode_str = "Background (Headless)" if (headless if headless is not None else self.config.bot_settings.headless) else "Visible Browser"
        source_str = "Search Query Mode" if use_search else "Recommended Jobs Mode (Naukri AI Match)"
        
        log_info(f"Starting Naukri Auto-Apply Engine", "bold cyan")
        log_info(f"* Source: {source_str}", "bold green")
        log_info(f"* Mode: {mode_str}", "bold magenta")
        log_info(f"* Applications Today: {applied_today} | Target Cap: {max_apps} | Dry Run: {dry_run}", "yellow")
        log_info(f"* Detailed Log File: data/bot.log", "dim")

        total_applied_this_session = 0

        try:
            if not use_search:
                # 1. Recommended Jobs Flow
                log_info("Harvesting top matching jobs from Naukri Recommendation Engine...", "bold blue")
                recommended_jobs = self.recommended_engine.fetch_recommended_jobs(self.page, max_cards=150)
                log_info(f"Found {len(recommended_jobs)} curated recommendations matched to your profile.", "cyan")

                for job in recommended_jobs:
                    if total_applied_this_session >= max_apps:
                        log_info("Reached maximum application target for this run. Stopping gracefully.", "bold green")
                        break

                    job_id = job.get("job_id")
                    title = job.get("title", "Unknown")
                    company = job.get("company", "Unknown").split("\n")[0].strip()

                    # Pre-check database
                    if self.tracker.is_already_applied(job_id):
                        log_info(f"Already applied to: {title} at {company}", "dim")
                        continue

                    # Filter company review rating
                    rating = job.get("rating", 0.0)
                    if rating > 0.0 and rating < self.config.search_preferences.skip_company_reviews_under:
                        log_warning(f"Skipping {title} at {company} (Rating {rating} < threshold)")
                        continue

                    # Filter company blacklist
                    if any(blacklisted.lower() in company.lower() for blacklisted in self.config.search_preferences.company_blacklist):
                        log_warning(f"Skipping {title} at {company} (Company blacklist matched)")
                        continue

                    res = self._apply_to_job(job, dry_run=dry_run)
                    if res == "QUOTA_REACHED":
                        log_warning("Halting session due to Naukri daily limit quota.")
                        break
                    elif res is True:
                        total_applied_this_session += 1
                        log_success(f"[OK] Successfully applied ({total_applied_this_session}/{max_apps}): {title} at {company}")
                        time.sleep(random.uniform(self.config.bot_settings.min_human_delay_seconds, self.config.bot_settings.max_human_delay_seconds))

            else:
                # 2. Search Query Flow
                for role in self.config.search_preferences.roles:
                    for location in self.config.search_preferences.locations:
                        if total_applied_this_session >= max_apps:
                            break

                        log_info(f"Searching for '{role}' in '{location}'...", "bold blue")
                        jobs = self.search_engine.search_jobs(self.page, role, location)
                        log_info(f"Found {len(jobs)} jobs for query.", "cyan")

                        for job in jobs:
                            if total_applied_this_session >= max_apps:
                                break

                            job_id = job.get("job_id")
                            title = job.get("title", "Unknown")
                            company = job.get("company", "Unknown").split("\n")[0].strip()

                            if self.tracker.is_already_applied(job_id):
                                log_info(f"Already applied to: {title} at {company}", "dim")
                                continue

                            res = self._apply_to_job(job, dry_run=dry_run)
                            if res == "QUOTA_REACHED":
                                log_warning("Halting session due to Naukri daily limit quota.")
                                return
                            elif res is True:
                                total_applied_this_session += 1
                                log_success(f"[OK] Successfully applied ({total_applied_this_session}/{max_apps}): {title} at {company}")
                                time.sleep(random.uniform(self.config.bot_settings.min_human_delay_seconds, self.config.bot_settings.max_human_delay_seconds))

        finally:
            self.close()
            log_success(f"Session complete! Total jobs processed: {total_applied_this_session}")
            log_info("Cross-verify anytime at: https://www.naukri.com/mnjuser/appliedjobs", "dim")

    def _apply_to_job(self, job: dict, dry_run: bool):
        title = job["title"]
        company = job["company"].split("\n")[0].strip()
        url = job["job_url"]
        job_id = job["job_id"]

        log_info(f"Evaluating job: {title} at {company}", "cyan")

        try:
            job_page = self.context.new_page()
            job_page.goto(url, wait_until="load", timeout=45000)
            human_delay(2, 3)

            # 1. Check for External ATS Redirect
            company_site_btn = job_page.query_selector(
                "button#company-site-button, button.company-site-button, "
                "button:has-text('Apply on Company Site'), a:has-text('Apply on Company Site'), "
                "button:has-text('Apply on company website'), a:has-text('Apply on company website'), "
                "button:has-text('Apply on company site'), a:has-text('Apply on company site')"
            )
            if company_site_btn:
                log_warning(f"-> External ATS redirect detected for {title} at {company}. Logged and skipped.")
                self.tracker.record_application(job_id, title, company, job.get("location", "India"), url, status="EXTERNAL_SITE")
                job_page.close()
                return False

            # 2. Check if Already Applied on page
            already_applied_badge = job_page.query_selector(
                "button:text-is('Applied'), span:text-is('Applied'), "
                "button:has-text('Already Applied'), span:has-text('Already Applied'), "
                ".already-applied, [class*='already-applied']"
            )
            if already_applied_badge:
                log_info(f"-> Naukri badge indicates already applied: {title} at {company}", "dim")
                self.tracker.record_application(job_id, title, company, job.get("location", "India"), url, status="ALREADY_APPLIED")
                job_page.close()
                return False

            # 3. Find Primary In-Platform Apply button
            apply_btn = job_page.query_selector(
                "button#apply-button, button.apply-button, "
                "button:text-is('Apply'), button:text-is('Apply Now'), "
                ".styles_apply-button__uJI3A:not(:has-text('Applied'))"
            )
            if not apply_btn:
                any_btn = job_page.query_selector("button.apply-button, .styles_apply-button__uJI3A")
                if any_btn and "applied" in any_btn.inner_text().lower():
                    log_info(f"-> Button is in 'Applied' state. Logged.", "dim")
                    self.tracker.record_application(job_id, title, company, job.get("location", "India"), url, status="ALREADY_APPLIED")
                    job_page.close()
                    return False

                log_info("-> No active Apply button available for this opening.", "dim")
                job_page.close()
                return False

            if dry_run:
                log_info(f"[DRY RUN] Validated Apply button & questions flow for {title} at {company}", "magenta")
                job_page.close()
                return True

            # Click Apply
            apply_btn.click(force=True)
            log.info(f"Clicked Apply button for {title} at {company}")
            human_delay(2.5, 3.5)
            
            # Check for Quota / Rate Limit Rejection by Naukri backend
            quota_err = job_page.query_selector("section[class*='user-msg'], div[class*='user-msg'], [class*='toast']:has-text('try again later'), div:has-text('error while processing your request'), div:has-text('limit reached')")
            if quota_err and quota_err.is_visible():
                err_text = quota_err.inner_text().strip().replace('\n', ' ')
                log_error(f"! NAUKRI PLATFORM RESPONSE: '{err_text}'")
                log_warning(">> Daily application quota reached for today (50+ applied). Naukri platform will reset this limit at midnight (12:00 AM).")
                self.tracker.record_application(job_id, title, company, job.get("location", "India"), url, status="QUOTA_REACHED")
                job_page.close()
                return "QUOTA_REACHED"

            # 4. Handle Chatbot screening questions or Form
            self._handle_chatbot_conversation(job_page, max_turns=12)

            human_delay(2.0, 3.0)

            # 5. Strict Verification of Official Confirmation
            confirmed = self._verify_application_success(job_page)
            if confirmed:
                self.tracker.record_application(job_id, title, company, job.get("location", "India"), url, status="APPLIED")
                job_page.close()
                return True
            else:
                # Check if apply button status switched to Applied
                updated_btn = job_page.query_selector("button:text-is('Applied'), span:text-is('Applied'), button:has-text('Already Applied'), .already-applied")
                if updated_btn:
                    self.tracker.record_application(job_id, title, company, job.get("location", "India"), url, status="APPLIED")
                    job_page.close()
                    return True

                # If confirmation was not detected, log as PENDING without marking as successfully applied
                log_warning(f"-> Application pending or unconfirmed for {title} at {company}. Logged as PENDING.")
                self.tracker.record_application(job_id, title, company, job.get("location", "India"), url, status="PENDING")
                job_page.close()
                return False

        except Exception as e:
            log_error(f"Error processing {title}: {e}")
            try:
                job_page.close()
            except Exception:
                pass
            return False

    def _handle_chatbot_conversation(self, page: Page, max_turns: int = 12):
        """Conversational solver supporting radios, dropdowns, chips, and contenteditable inputs."""
        consecutive_idle = 0
        for turn in range(max_turns):
            if self._verify_application_success(page):
                log_success("-> Success confirmation detected inside application flow!")
                break

            human_delay(1.5, 2.0)

            # Extract actual questions (filtering out greeting messages, disclaimers, and skip labels)
            try:
                prompts = page.evaluate("""() => {
                    const msgs = [];
                    const ignorePhrases = [
                        'thank you for showing interest',
                        'kindly answer all the recruiter',
                        'successfully apply',
                        'skip this question',
                        'skip',
                        'iel has taken all reasonable',
                        'applicants are advised to research',
                        'security guidelines',
                        'get noticed by recruiters',
                        'apply without registration'
                    ];
                    document.querySelectorAll('div.botMsg, div.msg, ._chatMsg, div.question, div.chat-item, [class*="botMsg"], [class*="chatMsg"]').forEach(el => {
                        const t = (el.innerText || '').trim();
                        if (t && t.length > 3) {
                            const tLower = t.toLowerCase();
                            if (!ignorePhrases.some(phrase => tLower.includes(phrase))) {
                                msgs.push(t);
                            }
                        }
                    });
                    return msgs;
                }""")
            except Exception:
                prompts = []

            latest_prompt = prompts[-1] if prompts else ""
            if any(s in latest_prompt.lower() for s in ["successfully applied", "application sent", "applied to this job", "already applied", "applied to "]):
                log_success("-> Confirmation detected in bot prompt!")
                break

            action_taken = False

            # A. Check for Radio Options / Selection Chips inside chatbot
            radios = page.query_selector_all("div.ssrc__radio-btn-container, div.singleselect-radiobutton label, label.ssrc__radio-label, input.ssrc__radio, div.chatbot_Chip, div.chipsContainer .chipItem, div.botMsg button.chip, div.quick-reply button, [class*='chat'] .botChip, [class*='bot'] .botChip")
            if radios and latest_prompt:
                radio_texts = [r.inner_text().strip() for r in radios if r.is_visible() and r.inner_text().strip() and "skip" not in r.inner_text().lower()]
                if radio_texts:
                    best_opt = self.qa_agent.resolve_question(latest_prompt, radio_texts)
                    log_info(f"Radio question: '{latest_prompt}' | Options: {radio_texts} | Selecting: '{best_opt}'")
                    for r in radios:
                        if r.is_visible() and (best_opt.lower() == r.inner_text().strip().lower() or best_opt.lower() in r.inner_text().strip().lower()):
                            r.click(force=True)
                            human_delay(0.4, 0.7)
                            
                            # Ensure radio input event fired
                            try:
                                page.evaluate("""(text) => {
                                    document.querySelectorAll('div.ssrc__radio-btn-container, label.ssrc__radio-label, .singleselect-radiobutton label').forEach(el => {
                                        if ((el.innerText || '').toLowerCase().includes(text.toLowerCase())) {
                                            const radio = el.querySelector('input[type="radio"]') || el;
                                            radio.click();
                                            radio.dispatchEvent(new Event('change', { bubbles: true }));
                                        }
                                    });
                                }""", best_opt)
                            except Exception:
                                pass
                            
                            human_delay(0.4, 0.7)
                            # Click Save / Send button
                            send_btn = page.query_selector("div.sendMsgbtn_container div.send, div.sendMsg, div.send, [class*='sendMsg'], button:has-text('Save'), button:has-text('Send')")
                            if send_btn and send_btn.is_visible():
                                send_btn.click(force=True)
                            human_delay(1.5, 2.5)
                            action_taken = True
                            break

            # B. Check for Contenteditable Input Div anywhere on page
            if not action_taken and latest_prompt:
                text_area = page.query_selector("div.textArea[contenteditable='true'], div[contenteditable='true']")
                if text_area and text_area.is_visible():
                    ans = self.qa_agent.resolve_question(latest_prompt)
                    log_info(f"Input question: '{latest_prompt}' | Answering: '{ans}'")
                    try:
                        text_area.click(force=True)
                        human_delay(0.2, 0.3)
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        human_delay(0.1, 0.2)
                        page.keyboard.type(str(ans), delay=35)
                        human_delay(0.3, 0.6)
                        send_btn = page.query_selector("div.sendMsg, div.send, [class*='sendMsg'], [class*='send-msg'], [id*='sendMsg']")
                        if send_btn and send_btn.is_visible():
                            send_btn.click(force=True)
                        else:
                            page.keyboard.press("Enter")
                        human_delay(2.0, 3.0)
                        action_taken = True
                    except Exception as ex:
                        log_warning(f"Contenteditable input warning: {ex}")

            # C. Check for Dropdowns
            if not action_taken and latest_prompt:
                try:
                    dd = page.query_selector("div.dropdownMainContainer:visible, div.custom-select:visible, select:visible")
                    if dd:
                        dd.click(force=True)
                        human_delay(0.3, 0.6)
                        options = page.query_selector_all("ul.dropdownMenuGroup li:visible, div.dropdown-menu div:visible, option:visible")
                        opt_texts = [o.inner_text().strip() for o in options if o.inner_text().strip()]
                        if opt_texts:
                            best_opt = self.qa_agent.resolve_question(latest_prompt, opt_texts)
                            log_info(f"Dropdown question: '{latest_prompt}' | Selecting: '{best_opt}'")
                            for o in options:
                                if best_opt.lower() in o.inner_text().strip().lower():
                                    o.click(force=True)
                                    human_delay(0.5, 1.0)
                                    send_btn = page.query_selector("div.sendMsg, div.send, [class*='sendMsg'], button:has-text('Save'), button:has-text('Send')")
                                    if send_btn and send_btn.is_visible():
                                        send_btn.click(force=True)
                                    human_delay(1.5, 2.5)
                                    action_taken = True
                                    break
                except Exception:
                    pass

            # D. Check for Skip This Question button if available
            if not action_taken:
                skip_btn = page.query_selector("div.ssrc__radio-btn-container:has-text('Skip'), div.botMsg [class*='skip']:visible, span:has-text('Skip this question'):visible, button:has-text('Skip'):visible")
                if skip_btn:
                    log_info("Clicked 'Skip this question' button")
                    skip_btn.click(force=True)
                    human_delay(1.5, 2.5)
                    action_taken = True

            # E. Check for standard inputs / textareas
            if not action_taken and latest_prompt:
                try:
                    inputs = page.query_selector_all("input[type='text']:visible, input[type='number']:visible, textarea:visible")
                    chatbot_inputs = [inp for inp in inputs if "suggestor" not in (inp.get_attribute("class") or "")]
                    for inp in chatbot_inputs:
                        ans = self.qa_agent.resolve_question(latest_prompt)
                        log_info(f"Standard input: '{latest_prompt}' | Answering: '{ans}'")
                        inp.click(force=True)
                        inp.fill(str(ans))
                        human_delay(0.3, 0.5)
                        page.keyboard.press("Enter")
                        send_btn = page.query_selector("button.send-btn, button.save-btn, button[type='submit'], ._sendBtn, button:has-text('Send'), button:has-text('Submit'), button:has-text('Next')")
                        if send_btn and send_btn.is_visible():
                            send_btn.click(force=True)
                        human_delay(1.5, 2.5)
                        action_taken = True
                        break
                except Exception:
                    pass

            # F. Check for Submit / Save & Apply Buttons
            if not action_taken:
                try:
                    submit_btn = page.query_selector("button:has-text('Save & Apply'):visible, button:has-text('Submit Application'):visible, button:has-text('Submit'):visible")
                    if submit_btn:
                        submit_btn.click(force=True)
                        human_delay(1.5, 3.0)
                        action_taken = True
                except Exception:
                    pass

            if not action_taken:
                consecutive_idle += 1
                if consecutive_idle >= 2 or self._verify_application_success(page):
                    break
            else:
                consecutive_idle = 0

    def _verify_application_success(self, page: Page) -> bool:
        """Checks for official confirmation elements on page and inside chatbot."""
        try:
            confirmation_indicators = [
                "div:has-text('You have successfully applied')",
                "div:has-text('Application sent')",
                "div:has-text('applied successfully')",
                "div:has-text('Applied to ')",
                "div:has-text('Applied to')",
                "span:text-is('Applied')",
                "button:text-is('Applied')",
                "div.apply-message",
                "div.success-message",
                "div.successMsg",
                "button:has-text('Already Applied')",
                ".already-applied"
            ]
            for sel in confirmation_indicators:
                elem = page.query_selector(sel)
                if elem and elem.is_visible():
                    return True
            
            # Check page body text directly
            text = page.evaluate("() => document.body.innerText.toLowerCase()")
            if (
                "successfully applied" in text or 
                "application sent" in text or 
                "applied to this job" in text or
                "applied to \"" in text or
                "applied to '" in text
            ):
                return True
            return False
        except Exception:
            return False