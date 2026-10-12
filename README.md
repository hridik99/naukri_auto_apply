# Naukri AI Auto-Apply Bot 🚀

An autonomous, human-simulating job application assistant for **Naukri.com** built with **Playwright (Python)** and **Google Gemini API (100% Free)**.

Pre-configured for **Hridik Gulati** (Full Stack Developer, Python/Django, Flutter, AWS).

---

## 🌟 Key Features

1. **Persistent Logged-in Session**:
   - Log in manually **once** with your credentials/OTP. 
   - Playwright retains your session cookies and local storage in `data/chrome_user_data/`, so you never need to deal with daily OTPs or captchas.
2. **AI Screening Q&A Engine**:
   - Accurately answers recruiter screening questions, salary inputs, notice period dropdowns, and multi-choice modals.
   - Deterministic fast rules for standard fields + **Google Gemini 2.0 Flash (Free tier)** fallback for open-ended questions.
3. **Anti-Detection & Human Simulation**:
   - Uses real Chrome instance parameters, removes `navigator.webdriver`, and injects random human-like delays (2.5–5.0 seconds).
4. **Application Tracker**:
   - Local SQLite database (`data/applications.db`) ensures you never apply to the same job twice and respect daily platform limits.
5. **Multi-Resume Support**:
   - Generate instant `config.json` profiles from **any new resume** (PDF or TXT) via `tools/profile_builder.py`.

---

## 🛠️ Step-by-Step Setup Guide

### 1. Install Dependencies
Open PowerShell or Terminal in the project root:
```bash
cd "C:\Users\HirdikGulati\.gemini\antigravity\scratch\naukri_auto_apply"
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Free Gemini API Key
1. Get your free API key from [Google AI Studio](https://aistudio.google.com/) (100% free, no credit card required).
2. Open `.env` and set your key:
```env
GEMINI_API_KEY=AIzaSyYourActualKeyHere...
```

### 3. One-Time Manual Login (Saves Session)
Run the login command:
```bash
python run.py --login
```
- A Chrome browser will open at Naukri login page.
- Enter your mobile/email, password, and OTP.
- Once you see your Naukri homepage/profile, return to the terminal and press `Enter`.
- Your session is now permanently saved.

---

## 🚀 Running the Bot

### 1. Recommended Jobs Mode (Default - Naukri AI Matched)
Applies directly from your personal [Naukri Recommended Jobs](https://www.naukri.com/mnjuser/recommendedjobs) feed:
```bash
# Silent Background Mode (Headless)
python run.py --run --max-jobs 50

# Visible Browser Window (To watch the bot interact live)
python run.py --run --max-jobs 50 --headed
```

### 2. Search Query Mode (Keyword & City Filtered)
Searches Naukri by target job titles, experience range, and cities defined in `config.json`:
```bash
python run.py --run --search --max-jobs 50 --headed
```

### 3. Dry-Run Mode (Safe Simulation)
Simulates navigating cards and answering questions without pressing final submit:
```bash
python run.py --dry-run --max-jobs 5 --headed
```

### 4. Application History & Status Dashboard
Inspect all applied jobs, timestamps, and direct links:
```bash
python run.py --status
```
You can also open:
- `data/applied_jobs.md` (Markdown log with clickable job links)
- `data/applied_jobs.csv` (Spreadsheet-compatible log)
- [Naukri Official Applied Jobs Page](https://www.naukri.com/mnjuser/appliedjobs)

---

## 🔑 How to Logout & Switch Accounts

To log out of the current Naukri account and connect a new account:

1. **Clear Saved Session**:
   ```bash
   python run.py --logout
   ```
2. **Log into New Account**:
   ```bash
   python run.py --login
   ```
   A Chrome window opens -> log into the new account with OTP/password -> press `Enter` in the terminal to save.

---

## ⚙️ How to Change Answers & Screening Responses

All screening answers are configured in [config.json](file:///C:/Users/HirdikGulati/.gemini/antigravity/scratch/naukri_auto_apply/config.json):

### 1. Salary & Notice Period Answers
| Field in `config.json` | Example Value | What it Answers in Naukri |
| :--- | :--- | :--- |
| `"current_ctc_lpa"` | `6.5` | Current Fixed CTC (e.g. ₹6.5 Lakhs / 650000) |
| `"expected_ctc_lpa"` | `10.0` | Expected CTC (e.g. ₹10.0 Lakhs / 1000000) |
| `"has_offer_in_hand"` | `true` | "Do you have an offer in hand?" -> Yes |
| `"offer_in_hand_ctc_lpa"` | `9.0` | "What is your holding offer CTC?" -> ₹9.0 LPA |
| `"notice_period_days"` | `30` | Notice period dropdowns & text fields (e.g. 1 Month / 30 Days) |
| `"total_experience_years"` | `3.5` | Overall experience in years |
| `"willing_to_relocate"` | `true` | Relocation preference questions |

### 2. Tech Stack & Skill Experience
Under `"skills_experience"`, define how many years of experience you have for each keyword:
```json
"skills_experience": {
    "python": 3.5,
    "django": 3.5,
    "react": 2.0,
    "flutter": 2.0,
    "aws": 2.0,
    "sql": 3.5,
    "docker": 1.5
}
```
*When Naukri asks: "How many years of experience do you have in Python?", the bot automatically inputs `3.5`.*

### 3. Search Keywords & City Preferences
Under `"search_preferences"`, customize the roles and locations for Search Mode:
```json
"search_preferences": {
    "roles": [
        "Full Stack Developer",
        "Python Developer",
        "Backend Developer",
        "Flutter Developer"
    ],
    "locations": [
        "Delhi / NCR",
        "Bangalore",
        "Hyderabad",
        "Remote"
    ],
    "min_experience_years": 2,
    "max_experience_years": 4,
    "max_applications_per_run": 50
}
```

---

## 🔄 Auto-Generate Config from Any New Resume

To automatically configure the bot for a new resume (PDF or TXT):
```bash
python tools/profile_builder.py path/to/new_resume.pdf config.json
```
The AI will extract all skills, CTC defaults, education, and target job titles and generate an updated `config.json`.

---

## ⚠️ Naukri Quota & Platform Tips
- **Daily Quota**: Naukri limits accounts to ~50 applications per 24 hours. The bot detects when this limit is reached and stops cleanly.
- **Midnight Reset**: Naukri resets the quota every night at 12:00 AM.
