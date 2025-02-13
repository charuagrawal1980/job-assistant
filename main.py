from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from config import Config
from managers import AirtableManager, LinkedInScraper, ResumeGenerator
from ui import GradioUI
from prompts import Prompts

def main():
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

    # Initialize components

    airtable_manager = AirtableManager()
    linkedin_scraper = LinkedInScraper(openai_llm)
    resume_generator = ResumeGenerator(gemini_llm)
    prompts = Prompts()
    # Create and launch UI
    ui = GradioUI(airtable_manager, linkedin_scraper, resume_generator, prompts)
    demo = ui.create_ui()
    demo.launch(debug=True)

if __name__ == "__main__":
    main()