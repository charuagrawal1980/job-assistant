from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from config import Config
from managers import AirtableManager, LinkedInScraper, ResumeGenerator, SheetManager
from ui import GradioUI
from prompts import Prompts
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

def main():
    sheetKey = '14-aYK1FmCmPwlOMAnxqpe7ZIweXUC3URlXUrAXEY_qI'
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive'] 
    creds = ServiceAccountCredentials.from_json_keyfile_name('secrets.json')
    client = gspread.authorize(creds)
    sheet_manager = SheetManager(client, sheetKey)
    # Initialize LLMs
    gemini_llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=Config.GEMINI_API_KEY,
        temperature=Config.CREATIVITY_LEVEL
    )
    
    openai_llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0.0,
        timeout=100,
        api_key=Config.OPENAI_API_KEY
    )

    

    airtable_manager = AirtableManager()
    linkedin_scraper = LinkedInScraper(openai_llm)
    resume_generator = ResumeGenerator(gemini_llm)

    prompts = Prompts()
    # Create and launch UI
    ui = GradioUI(airtable_manager, linkedin_scraper, resume_generator, prompts, sheet_manager)
    demo = ui.create_ui()
    demo.launch(debug=True)

if __name__ == "__main__":
    main()