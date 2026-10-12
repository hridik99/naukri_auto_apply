import sqlite3
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "applications.db"
CSV_PATH = DATA_DIR / "applied_jobs.csv"
MD_PATH = DATA_DIR / "applied_jobs.md"

class ApplicationTracker:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.csv_path = CSV_PATH
        self.md_path = MD_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._init_files()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applied_jobs (
                    job_id TEXT PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    location TEXT,
                    job_url TEXT,
                    status TEXT,
                    applied_date TEXT,
                    questions_answered TEXT
                )
            """)
            conn.commit()

    def _init_files(self):
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Company", "Job Title", "Location", "Status", "Job URL"])

        if not self.md_path.exists():
            with open(self.md_path, "w", encoding="utf-8") as f:
                f.write("# Naukri Applied Jobs Log\n\n")
                f.write("| Timestamp | Company | Job Title | Location | Status | Job Link |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

    def is_already_applied(self, job_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM applied_jobs WHERE job_id = ?", (job_id,))
            return cursor.fetchone() is not None

    def record_application(self, job_id: str, title: str, company: str, location: str, job_url: str, status: str = "APPLIED", questions: str = ""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO applied_jobs (job_id, title, company, location, job_url, status, applied_date, questions_answered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, title, company, location, job_url, status, timestamp, questions))
            conn.commit()

        # Append to CSV
        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, company, title, location, status, job_url])
        except Exception:
            pass

        # Append to Markdown
        try:
            safe_title = title.replace("|", "-")
            safe_company = company.replace("|", "-")
            safe_loc = location.replace("|", "-")
            md_link = f"[{safe_title}]({job_url})" if job_url else safe_title
            with open(self.md_path, "a", encoding="utf-8") as f:
                f.write(f"| {timestamp} | **{safe_company}** | {md_link} | {safe_loc} | `{status}` | [Open Job]({job_url}) |\n")
        except Exception:
            pass

    def get_todays_count(self) -> int:
        today_str = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM applied_jobs WHERE applied_date LIKE ? AND status = 'APPLIED'", (f"{today_str}%",))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_summary(self, limit: int = 50) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM applied_jobs ORDER BY applied_date DESC LIMIT {limit}")
            return [dict(row) for row in cursor.fetchall()]
