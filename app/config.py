import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class Education(BaseModel):
    degree: str = "B.Tech"
    branch: str = "Computer Science & Engineering"
    institution: str = "GGSIPU"
    graduation_year: int = 2023
    percentage_or_cgpa: str = "88%"

class CandidateProfile(BaseModel):
    full_name: str
    email: str
    phone: str
    current_location: str
    preferred_locations: List[str] = Field(default_factory=list)
    willing_to_relocate: bool = True
    total_experience_years: float = 3.0
    current_job_title: str
    current_company: str
    current_ctc_lpa: float
    expected_ctc_lpa: float
    has_offer_in_hand: bool = True
    offer_in_hand_ctc_lpa: float = 9.0
    notice_period_days: int = 30
    highest_education: Education
    gender: str = "Male"
    skills_experience: Dict[str, float] = Field(default_factory=dict)
    professional_summary: str = ""

class SearchPreferences(BaseModel):
    roles: List[str] = Field(default_factory=lambda: ["Full Stack Developer", "Python Developer"])
    locations: List[str] = Field(default_factory=lambda: ["Delhi / NCR", "Remote"])
    min_experience_years: int = 1
    max_experience_years: int = 4
    max_applications_per_run: int = 25
    skip_company_reviews_under: float = 0.0
    company_blacklist: List[str] = Field(default_factory=list)

class BotSettings(BaseModel):
    headless: bool = False
    slow_mo_ms: int = 100
    min_human_delay_seconds: float = 2.0
    max_human_delay_seconds: float = 5.0
    dry_run: bool = False

class AppConfig(BaseModel):
    candidate: CandidateProfile
    search_preferences: SearchPreferences
    bot_settings: BotSettings

def load_config(config_path: Optional[str] = None) -> AppConfig:
    if not config_path:
        base_dir = Path(__file__).resolve().parent.parent
        config_path = str(base_dir / "config.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return AppConfig(**data)
