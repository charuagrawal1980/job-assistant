from typing import Dict, List, Optional
from datetime import datetime
import logging
from pyairtable import Api
from pyairtable.formulas import match
import json
from config import Config
from utils import get_resume_text
from prompts import TAILORING_PROMPT, JOB_SEARCH_PROMPT
from browser_use import BrowserConfig, Browser, Agent

logger = logging.getLogger(__name__)

class AirtableManager:
    def __init__(self):
        """Initialize Airtable connection."""
        self.api = Api(api_key=Config.AIRTABLE_TOKEN)
        self.table = self.api.table(Config.AIRTABLE_BASE_ID, Config.AIRTABLE_TABLE_NAME)

    def get_all_records(self) -> List[Dict]:
        """Fetch all records from Airtable."""
        try:
            return self.table.all()
        except Exception as e:
            logger.error(f"Error fetching records: {str(e)}", exc_info=True)
            return []

    def get_new_records(self) -> List[Dict]:
        """Fetch records with 'new' status."""
        try:
            formula = match({"status": 'new'})
            return self.table.all(formula=formula)
        except Exception as e:
            logger.error(f"Error fetching new records: {str(e)}", exc_info=True)
            return []

    def update_record(self, record_id: str, updated_fields: Dict) -> Dict:
        """Update a specific record in Airtable."""
        try:
            return self.table.update(record_id, updated_fields)
        except Exception as e:
            logger.error(f"Error updating record: {str(e)}", exc_info=True)
            return {}

    def add_new_record(self, job_profile: Dict) -> Dict:
        """Add a new job profile record to Airtable."""
        try:
            new_fields = {
                "job_title": f"{job_profile['job_title']} at {job_profile['company_name']} in {job_profile['job_location']}",
                "job_description": f"{job_profile['job_description']}",
                "tailored_resume": "",
                "status": "new",
                "created_date": datetime.now().isoformat(),
            }
            return self.table.create(new_fields)
        except Exception as e:
            logger.error(f"Error adding new record: {str(e)}", exc_info=True)
            return {}

class LinkedInScraper:
    def __init__(self, llm):
        """Initialize LinkedIn scraper."""
        self.username = Config.USERNAME
        self.password = Config.PASSWORD
        self.llm = llm
        self.config = BrowserConfig(headless=True)
        self.browser = Browser(config=self.config)

    async def run_job_search(self, job_count: int) -> Dict:
        """
        Run LinkedIn job search and return results.
        
        Args:
            job_count: Number of jobs to scrape
            
        Returns:
            Dict containing job information
        """
        try:
            task = JOB_SEARCH_PROMPT.format(
                username=self.username,
                password=self.password,
                job_count=job_count
            )
            agent = Agent(task=task, llm=self.llm)
            result = await agent.run()
            response = result.final_result()
            
            try:
                jobs = json.loads(response)
            except json.JSONDecodeError as e:
                error_json = {
                    "error": "JSON Decode Error",
                    "message": str(e),
                    "response": response,
                    "location": "LinkedInScraper.run_job_search"
                }
                logger.error(json.dumps(error_json, indent=2))
                return {}
                
            return jobs
            
        except Exception as e:
            logger.error(f"Error in job search: {str(e)}", exc_info=True)
            return {}

class ResumeGenerator:
    def __init__(self, llm):
        """Initialize resume generator."""
        self.llm = llm

    def generate_tailored_resume(
        self, 
        resume_filename: str, 
        job_description: str
    ) -> str:
        """
        Generate a tailored resume based on job description.
        
        Args:
            resume_filename: Path to original resume
            job_description: Job description to tailor resume for
            
        Returns:
            str: Tailored resume content
        """
        try:
            resume_text = get_resume_text(resume_filename)
            final_prompt = TAILORING_PROMPT.format(
                job_description=job_description,
                resume_text=resume_text
            )
            return self.llm.invoke(final_prompt).content
        except Exception as e:
            logger.error(f"Error generating resume: {str(e)}", exc_info=True)
            return ""