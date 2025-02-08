from typing import Dict, List, Optional
from datetime import datetime
import logging
from pyairtable import Api
from pyairtable.formulas import match
import json
from config import Config
from utils import get_resume_text, get_wordfile_markdown
from prompts import TAILORING_PROMPT, JOB_SEARCH_PROMPT, TAILORING_PROMPT_1
from browser_use import BrowserConfig, Browser, Agent
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from decimal import Decimal

logger = logging.getLogger(__name__)

class TailoredResume(BaseModel):
    Before: Decimal
    After: Decimal
    Changes: str
    TailoredResume: str

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

    def get_all_records_by_customer(self, customer_email) -> List[Dict]:
      
        try:
            formula = match({"customer_email_address": customer_email})
            return self.table.all(formula=formula)
        except Exception as e:
            logger.error(f"Error fetching records: {str(e)}", exc_info=True)
            return []
    
    def get_all_records_by_customer_today(self, customer_email) -> List[Dict]:
      
        try:
            today_date = datetime.now().date().isoformat()  # Get today's date in ISO format
            # Create a formula string to match the date part
            formula_string = "AND({customer_email_address} = '{}', IS_SAME({createdDate}, '{}', 'day'))".format(customer_email, today_date)
            #formula = match({
            #"customer_email_address": customer_email,
            #"createdDate": today_date
            #})
           
            return self.table.all(formula=formula_string)
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

    def add_new_record(self, job_profile: Dict, filename, customer_name, customer_email_address) -> Dict:
   
        try:
            resume_text = get_wordfile_markdown(filename)
            new_fields = {
                "job_title": job_profile['job_title'],
                "job_description": f"{job_profile['job_description']}",
                "tailored_resume": "",
                "status": "new",
                "created_date": datetime.now().isoformat(),
                'company_name': job_profile['company_name'],
                'original_resume': resume_text,
                'customer_name': customer_name,
                'customer_email_address': customer_email_address,
                'job_url':job_profile['job_url']

            }
            return self.table.create(new_fields)
        except Exception as e:
            logger.error(f"Error adding new record: {str(e)}", exc_info=True)
            return {}

    def update_state_to_applied(self, selected_row):
        selectedrow = selected_row
        selectedrow["status"] = "applied"
        return ""

class LinkedInScraper:
    def __init__(self, llm):
        """Initialize LinkedIn scraper."""
        self.username = Config.USERNAME
        self.password = Config.PASSWORD
        self.llm = llm
        self.config = BrowserConfig(headless=True)
        self.browser = Browser(config=self.config)

    async def run_job_search(self, job_count: int) -> Dict:
      
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

    def clean_llm_response(self, response: str) -> dict:
        try:
            # Remove markdown code block indicators and newlines
            cleaned = response.replace('```json', '').replace('```', '').strip()
            # Parse the cleaned string into JSON
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {"json_error"}
        
    def generate_tailored_resume_markdown(
        self, 
        resume_filename: str, 
        job_description: str
    ) -> str:
       
        try:
            resume_text = get_wordfile_markdown(resume_filename)
            final_prompt = TAILORING_PROMPT_1.format(
                resume_text=resume_text,
                job_description=job_description
            )
            parser = PydanticOutputParser(pydantic_object=TailoredResume)
            chain = self.llm | parser
            #response = (self.llm.invoke(final_prompt).content)
            response = chain.invoke(final_prompt)
            #cleaned_response = self.clean_llm_response(response)
            #if cleaned_response.values[0]=="json_error": 
             #   response = (self.llm.invoke(final_prompt).content)
              #  cleaned_response = self.clean_llm_response(response)
            return response
        except Exception as e:
            logger.error(f"Error generating resume: {str(e)}", exc_info=True)
            return "error"
        

    def generate_tailored_resume(
        self, 
        resume_filename: str, 
        job_description: str
    ) -> str:
       
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