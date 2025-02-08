import logging
from datetime import datetime
from fpdf import FPDF
import pdfplumber
import pandas as pd
import mammoth
import markdownify
import markdown
from spire.doc import *
from spire.doc.common import *
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_wordfile_markdown(filename)->str:
    with open(filename, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
        markdown = markdownify.markdownify(html)
        return markdown
    
def save_markdowntext_to_word(markdown_text, state):
    filename = state if state else f"tailored_resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    html = markdown.markdown(markdown_text)
    with open("output.md", "w", encoding='utf-8') as md_file:
        md_file.write(html)
    document = Document()
    document.LoadFromFile("output.md")
    document.SaveToFile(filename, FileFormat.Docx2019)
    return filename

def save_resume_to_pdf(text: str) -> str:

    if not text:
        return None
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    lines = text.split('\n')
    for line in lines:
        pdf.multi_cell(0, 10, txt=line)
    
    filename = f"tailored_resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

def get_resume_text(resume_filename: str) -> str:

    resume_text = ""
    try:
        if resume_filename.endswith(".pdf"):
            with pdfplumber.open(resume_filename) as pdf:
                resume_text = " ".join(
                    page.extract_text() for page in pdf.pages if page.extract_text()
                )
        else:
            with open(resume_filename, "r") as file:
                resume_text = file.read()
        return resume_text
    except Exception as e:
        logger.error(f"Error extracting resume text: {str(e)}", exc_info=True)
        return ""
    
def get_jobs_from_excel(fileame):
        df = pd.read_excel(fileame)
        json_data = []
    
        for _, row in df.iterrows():
            job_entry = {
            "company_name": str(row['company_name']).strip(),
            "job_location": "",
            "job_description": str(row['job_description']).strip(),
            "job_title":row['job_title']
        }
            json_data.append(job_entry)
    
        return json_data