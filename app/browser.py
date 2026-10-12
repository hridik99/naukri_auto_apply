import os
import random
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Page

USER_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "chrome_user_data"

def get_browser_context(headless: bool = False, slow_mo: int = 100) -> tuple:
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    p = sync_playwright().start()
    
    # When headless is requested, we launch a real Chrome instance positioned offscreen
    # to bypass Akamai/Cloudflare Edge WAF TLS fingerprinting while remaining completely unobtrusive
    extra_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-infobars",
        "--disable-dev-shm-usage"
    ]
    
    if headless:
        extra_args.append("--window-position=3000,3000")
        actual_headless = False
    else:
        actual_headless = False

    # Launch persistent context using installed Chrome for natural fingerprints
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=actual_headless,
        slow_mo=slow_mo,
        channel="chrome",
        viewport={"width": 1366, "height": 768},
        args=extra_args
    )
    
    # Apply anti-bot stealth scripts across all tabs in the context
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    """)
    page = context.pages[0] if context.pages else context.new_page()
    return p, context, page

def human_delay(min_sec: float = 1.5, max_sec: float = 3.5):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

def human_type(page: Page, selector: str, text: str):
    page.click(selector)
    time.sleep(random.uniform(0.2, 0.5))
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.03, 0.09))
