from typing import Dict, List, Optional
from datetime import datetime
import logging
from pyairtable import Api
from pyairtable.formulas import match
import json
from config import Config
from utils import get_resume_text, get_wordfile_markdown
from prompts import TAILORING_PROMPT, JOB_SEARCH_PROMPT, TAILORING_PROMPT_1
#from browser_use import BrowserConfig, Browser, Agent
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from decimal import Decimal
from prompts import Prompts
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import uuid
from crew import LatestAiDevelopmentCrew, TailoredResume

logger = logging.getLogger(__name__)



class SheetManager:
    def __init__(self,client, sheetKey) -> None:
       
        sheet = client.open_by_key(sheetKey)
        self.sheet_instance = sheet.get_worksheet(0)
        
    def get_all_records_by_customer(self, customer_email) -> List[Dict]:
        """Fetch all records from Google sheets."""
        try:
            
            all_records = self.sheet_instance.get_all_records()
            filtered_data = [d for d in all_records if d['customer_email_address'] == customer_email]
            return filtered_data
        except Exception as e:
            logger.error(f"Error fetching records: {str(e)}", exc_info=True)
            return []
        
    def get_all_records(self) -> List[Dict]:
        """Fetch all records from Google sheets."""
        try:
            
            records_data = self.sheet_instance.get_all_records()
            return records_data
        except Exception as e:
            logger.error(f"Error fetching records: {str(e)}", exc_info=True)
            return []
        
    def get_all_records_for_tailoring(self) -> List[Dict]:
        """Fetch records with 'new' status."""
        try:
            filtered_data=[]
            all_records= self.sheet_instance.get_all_records()
            for d in all_records:
                status = d['status']
                if status=='new':
                    filtered_data.append(d)
            return filtered_data#filtered_data = [d for d in all_records if d['status'] == 'new']
        except Exception as e:
            logger.error(f"Error fetching new records: {str(e)}", exc_info=True)
            return []
           
    def add_new_record(self, job_profile: Dict, filename, customer_name, customer_email_address) -> Dict:
            try:
                new_record = self.create_new_record_data(job_profile, filename, customer_name,customer_email_address)
                return self.sheet_instance.append_row (new_record)
            except Exception as e:
                logger.error(f"Error adding new record: {str(e)}", exc_info=True)
                return {}
            
    def create_new_record_data(self,job_profile, filename, customer_name, customer_email_address):
        resume_text = get_wordfile_markdown(filename)
        new_fields = {
                "record_id": str(uuid.uuid4()),
                "job_title": job_profile['job_title'],
                "job_description": f"{job_profile['job_description']}",
                "tailored_resume": "",
                "before":"",
                "after":"",
                "changes":"",
                "status": "new",
                "created_date": datetime.now().isoformat(),
                'company_name': job_profile['company_name'],
                'original_resume': resume_text,
                'customer_name': customer_name,
                'customer_email_address': customer_email_address,
                'job_url':job_profile['job_url'],
                'tailored_resume_filename':''

            }
        row_data = [new_fields["record_id"], new_fields["job_title"], new_fields["job_description"], new_fields["tailored_resume"],
                    new_fields["before"], new_fields["after"], new_fields["changes"],
                 new_fields["status"], new_fields["created_date"], new_fields['company_name'], new_fields['original_resume'],
                   new_fields['customer_name'], new_fields['customer_email_address'], new_fields['job_url'], new_fields['tailored_resume_filename']]
        return row_data
    
    def update_record(self, record_id, updated_fields):
        """Update a specific record in the Google Sheet based on the given ID."""
        try:
            # Fetch all records from the sheet
            all_records = self.sheet_instance.get_all_records()

            # Find the index of the row with the matching ID
            row_index = None
            for i, record in enumerate(all_records):
                if record['record_id'] == record_id:  # Assuming 'id' is the column name for the ID
                    row_index = i + 2  # gspread uses 1-based indexing, and we skip the header row
                    break

            if row_index is not None:
             
                current_row = all_records[row_index - 2]  # Get the current row data

                # Update the current row with new values from updated_fields
                for key, value in updated_fields.items():
                    if key in current_row:  # Only update if the key exists in the current row
                        current_row[key] = value

                # Prepare the data to be written back to the sheet
                row_data = list(current_row.values())  # Convert the updated row back to a list

                # Update the row in the sheet
                self.sheet_instance.update(f'A{row_index}:O{row_index}', [row_data])  # Adjust the range as needed

            else:
                raise ValueError(f"Record with ID {record_id} not found.")

        except Exception as e:
            logger.error(f"Error updating record with ID {record_id}: {str(e)}", exc_info=True)
    


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
        #self.config = BrowserConfig(headless=True)
        #self.browser = Browser(config=self.config)

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
        self.prompts = Prompts()
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
        job_description: str,
        prompts:Prompts
    ) -> str:
       
        try:
            new_prompt = prompts.get_tailoring_prompt()
            resume_text = get_wordfile_markdown(resume_filename)
            final_prompt = new_prompt.format(
                resume_text=resume_text,
                job_description=job_description
            )
            crew = LatestAiDevelopmentCrew(resume_text, job_description)
            output =crew.crew().kickoff().raw
            clean_json_string = output.strip().rstrip("Processed after kickoff.'").strip("'")
            #parser = PydanticOutputParser(pydantic_object=TailoredResume)
            #chain = self.llm | parser
            #response = chain.invoke(final_prompt)
            out = json.loads(clean_json_string)
            return out
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