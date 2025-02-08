import gradio as gr
import pandas as pd
from typing import Tuple
import logging
from datetime import datetime

from utils import save_resume_to_pdf, save_markdowntext_to_word
from utils import get_jobs_from_excel
logger = logging.getLogger(__name__)

class GradioUI:
    def __init__(self, airtable_manager, linkedin_scraper, resume_generator):
        """Initialize Gradio UI components."""
        self.airtable_manager = airtable_manager
        self.linkedin_scraper = linkedin_scraper
        self.resume_generator = resume_generator

    def get_dashboard_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
       
        try:
            records = self.airtable_manager.get_all_records()
            df = pd.DataFrame(columns=[
                'record_id', 'job_title', 'resume_generated_date', 'original_resume','company_name',
                'status', 'tailored_resume', 'before','after','changes', 'created_date', 
                'job_description'
            ])
            
            for record in records:
                fields = record["fields"]
                row_data = {
                    'record_id': record["id"],
                    'job_title': fields.get('job_title'),
                    'resume_generated_date': fields.get('resume_generated_date'),
                    'original_resume': fields.get('original_resume'),
                    'status': fields.get('status'),
                    'company_name':fields.get('company_name'),
                    'tailored_resume': fields.get('tailored_resume'),
                    'before': fields.get('before'),
                    'after':fields.get('after'),
                    'changes':fields.get('changes'),
                    'created_date': fields.get('created_date'),
                    'job_description': fields.get('job_description')
                }
                df.loc[len(df)] = row_data
            
            # Create display DataFrame with hidden columns
            display_df = df[['record_id', 'job_title', 'before','after','resume_generated_date', 
                           'status', 'created_date']]
            
            return display_df, df
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
            return pd.DataFrame(), pd.DataFrame()

    def df_select_callback(self, full_df: pd.DataFrame, evt: gr.SelectData) -> Tuple[str, str]:
        """Handle DataFrame row selection."""
        record_id = evt.row_value[0]
        full_df_record = full_df.loc[full_df['record_id'] == record_id]   
        job_description = full_df_record['job_description']
        download_filename  = full_df_record.iloc[0]['company_name'] or "" +  "_" + full_df_record.iloc[0]['job_title']
        return (
            full_df_record.iloc[0]['job_description'], 
            full_df_record.iloc[0]['tailored_resume'], 
            full_df_record.iloc[0]['changes'],
            download_filename
        )

    async def process_files(
        self, 
        resume_file: str, 
        excel_file:str,
        job_links_file: str, 
        job_search_type: str, 
        job_count: int
    ) -> str:
        """Process resume and job files."""
        jobs={}
        try:
            if job_search_type == "Search":
                jobs = await self.linkedin_scraper.run_job_search(job_count)
               
            else:
                jobs = get_jobs_from_excel(excel_file)
            for job in jobs:
                    self.airtable_manager.add_new_record(job, resume_file)
            new_records = self.airtable_manager.get_new_records()
            for record in new_records:
                fields = record["fields"]
                tailored_response = self.resume_generator.generate_tailored_resume_markdown(
                    resume_file,
                    
                    fields["job_title"] + "\n" + fields["job_description"]
                )
                
                updated_fields = {
                    "tailored_resume": tailored_response.get("tailored_resume"),
                    "status": "resume_generated",
                    "resume_generated_date": datetime.now().isoformat(),
                    "before": tailored_response.get("before"),
                    "after":tailored_response.get("after"),
                    "changes":tailored_response.get("changes"),
                    
                }
                self.airtable_manager.update_record(record["id"], updated_fields)
                
            return "Process complete!"
            
        except Exception as e:
            logger.error(f"Error processing files: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"

    def create_ui(self):
        """Create and configure Gradio UI."""
        with gr.Blocks(fill_height=True) as demo:
            gr.Markdown("# Resume Tailoring Dashboard")
            
            with gr.Row():
                with gr.Column(scale=1):
                    pdf_input = gr.File(label="Upload Resume", file_types=[".docx"])
                    excel_input = gr.File(label="Upload Jobs", file_types=[".xlsx"])
                    rb_job_type = gr.Radio(
                        ["Search","Upload"], 
                        label="Upload Job Links", 
                        value="Upload"
                    )
                    job_count = gr.Number(label="Number of Jobs", value=3)
                    start_button = gr.Button("Start Processing")
                    refresh_button = gr.Button("Refresh Grid")

                with gr.Column(scale=5):
                    full_df_state = gr.State()
                    dashboard = gr.DataFrame(None)
                    
                    with gr.Row():
                        job_description = gr.Textbox(label="Job Description")
                        with gr.Column():
                            download_filename = gr.Textbox(label="download file name")
                            tailored_resume = gr.Textbox(label="Tailored Resume")
                            download_button = gr.Button("Download Resume")
                            tailored_resume_pdf = gr.File(
                                label="Download Tailored Resume")
                    with gr.Row():
                        changes =gr.Textbox(label="Tailored Resume")       

            # Event handlers
            download_button.click(
                fn=save_markdowntext_to_word,
                inputs=[tailored_resume, gr.State()],
                outputs=[tailored_resume_pdf]
            )

            demo.load(
                fn=self.get_dashboard_data,
                outputs=[dashboard, full_df_state]
            )

            start_button.click(
                fn=self.process_files,
                inputs=[
                    pdf_input, 
                    excel_input,
                    gr.State(None), 
                    rb_job_type, 
                    job_count
                ],
                outputs=[gr.Textbox()]
            )

            refresh_button.click(
                fn=self.get_dashboard_data,
                outputs=[dashboard, full_df_state]
            )

            dashboard.select(
                fn=self.df_select_callback,
                inputs=[full_df_state],
                outputs=[job_description, tailored_resume, changes, download_filename]
            )

        return demo