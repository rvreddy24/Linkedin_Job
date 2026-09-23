"""Configuration loader for Auto Bot LinkedIn Job."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


def load_json_file(file_path: Path, default: dict) -> dict:
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}")
    return default


# Load Hunt Config
HUNT_CONFIG_PATH = BASE_DIR / "config" / "hunt_config.json"
DEFAULT_HUNT_CONFIG = {
    "operator_name": "Hrishith Raj Reddy Malgireddy",
    "keywords_include": [
        "Forward Deployed", "Forward Deployed Engineer", "Forward Deployed AI",
        "AI Solutions Engineer", "GenAI Solutions Engineer", "GenAI Engineer",
        "Generative AI Engineer", "LLM Engineer", "AI Agent Engineer",
        "AI Systems Engineer", "AI Application Developer", "Full Stack AI Engineer",
        "Applied AI Engineer", "RAG Engineer", "Prompt Engineer",
        "Machine Learning Engineer", "AI Software Engineer", "Founding AI Engineer",
        "Founding Software Developer", "AI Engineer", "Python AI Developer", "AI Developer"
    ],
    "keywords_exclude_title": [
        "Hardware Engineer", "Mechanical Engineer", "Civil Engineer",
        "Nurse", "Therapist", "Psychotherapist", "Dental", "Accountant", "Payroll",
        "Customer Service", "Customer Support", "Sales Representative",
        "Account Executive", "Retail", "Legal Counsel", "Recruiter",
        "Talent Partner", "Project Scheduler", "Billing Specialist"
    ],
    "countries": ["US"],
    "types": ["full-time", "part-time", "contract"],
    "posted_within_hours": 24,
    "posted_within_days": 1,
    "jobspipe_limit": 25,
    "jobspipe_queries": [
        ["Forward Deployed Engineer", "AI Solutions Engineer", "GenAI Engineer"],
        ["LLM Engineer", "AI Agent Engineer", "RAG Engineer"],
        ["AI Software Engineer", "Full Stack AI Engineer", "Applied AI"]
    ],
    "keep_score_min": 55,
    "hot_score_min": 80,
    "cooldown_days": 21,
    "max_score_per_run": 20,
    "description_max_chars": 6000,
    "agency_name_hints": ["recruitment", "recruiting", "staffing", "search firm", "talent partners"]
}

HUNT_CONFIG = load_json_file(HUNT_CONFIG_PATH, DEFAULT_HUNT_CONFIG)

# Load Operator Positioning Profile
POSITIONING_PATH = BASE_DIR / "config" / "operator_positioning_template.json"
DEFAULT_POSITIONING = {
    "operator_name": "Hrishith Raj Reddy Malgireddy",
    "one_sentence_offer": "Forward Deployed AI Engineer delivering production GenAI/LLM systems, AI agent workflows, RAG architectures, and scalable APIs directly alongside engineering and startup leadership.",
    "what_we_sell": [
        "Forward Deployed AI Engineering and rapid technical prototyping directly alongside product and founder teams",
        "Production GenAI & RAG systems (LangChain, Vector Search, document processing pipelines, evaluation metrics)",
        "Autonomous AI agent workflows and developer tooling (Claude Code, Cursor, MCP servers, prompt engineering)",
        "Scalable backend services, REST APIs, and cloud deployments (Python, Django, FastAPI, Node.js, PostgreSQL, GCP, Docker, Terraform)"
    ],
    "who_we_want": [
        "US companies hiring Forward Deployed Engineers, AI Solutions Engineers, GenAI / LLM Engineers, AI Agent Engineers, Full-Stack AI Engineers, or Founding AI Developers",
        "Founders, CTOs, and Heads of Engineering needing hands-on engineers who build and ship production AI systems rapidly"
    ],
    "who_we_do_not_want": [
        "Non-US or offshore roles",
        "Non-technical roles (sales, customer support, recruitment, marketing, healthcare clinical)",
        "Hardware, mechanical, or civil engineering positions"
    ],
    "proof_points": [],
    "draft_signature": "Best regards,\nHrishith Raj Reddy Malgireddy\nAI Forward Deployed Engineer\nPhone: +1-573-639-3854 | Email: hrishithrajreddy22@gmail.com\nLinkedIn: https://www.linkedin.com/in/hrishith-raj-reddy-malgireddy-919750262/\nPortfolio: https://portfolio-app-mm1d.vercel.app/\nGitHub: https://github.com/hrishith30",
    "profile_url": "https://www.linkedin.com/in/hrishith-raj-reddy-malgireddy-919750262/"
}

POSITIONING_CONFIG = load_json_file(POSITIONING_PATH, DEFAULT_POSITIONING)

# API Keys and Environment Variables
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
JOBSPIPE_API_KEY = os.getenv("JOBSPIPE_API_KEY", "")
GOOGLE_SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID", "")
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
