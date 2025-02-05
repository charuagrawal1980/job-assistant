import logging
from datetime import datetime
from fpdf import FPDF
import pdfplumber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_resume_to_pdf(text: str) -> str:
    """
    Saves resume text to a PDF file.
    
    Args:
        text: Resume text content
        
    Returns:
        str: Generated PDF filename
    """
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
    """
    Extracts text from a resume file.
    
    Args:
        resume_filename: Path to resume file
        
    Returns:
        str: Extracted text content
    """
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