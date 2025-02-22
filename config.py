import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
    AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
    AIRTABLE_TABLE_NAME = "resumes"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    CREATIVITY_LEVEL = 0.3
    CLAUDE_API_KEY= os.getenv("CLAUDE_API_KEY")