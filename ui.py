import gradio as gr
import pandas as pd
from typing import Tuple
import logging
from datetime import datetime

from utils import save_resume_to_pdf, save_markdowntext_to_word, download_all_resumes
from utils import get_jobs_from_excel
logger = logging.getLogger(__name__)

class GradioUI:
    full_df_state: pd.DataFrame
    selected_row: gr.SelectData
    selected_record_id: str
    def __init__(self, airtable_manager, linkedin_scraper, resume_generator):
        """Initialize Gradio UI components."""
        self.airtable_manager = airtable_manager
        self.linkedin_scraper = linkedin_scraper
        self.resume_generator = resume_generator
        self.selected_row = None
        
    def get_dashboard_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
       
        try:
            records = self.airtable_manager.get_all_records()
            df = pd.DataFrame(columns=[
                'record_id','customer_name', 'customer_email_address', 'job_title', 'job_url','resume_generated_date', 'original_resume','company_name',
                'status', 'tailored_resume', 'before','after','changes', 'tailored_resume_filename', 'created_date', 
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
                    'job_description': fields.get('job_description'),
                    'tailored_resume_filename':fields.get('tailored_resume_filename'),
                    'customer_name': fields.get('customer_name'),
                    'customer_email_address': fields.get('customer_email_address'),
                    'job_url': fields.get('job_url')
                }
                df.loc[len(df)] = row_data
            
            # Create display DataFrame with hidden columns
            display_df = df[['company_name', 'job_title', 'job_url', 'before','after', 
                           'status', 'created_date', 'record_id']]
            
            return display_df, df
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
            return pd.DataFrame(), pd.DataFrame()

    def df_select_callback(self, full_df: pd.DataFrame, evt: gr.SelectData) -> Tuple[str, str]:
        """Handle DataFrame row selection."""
        self.selected_record_id = evt.row_value[7]
        self.selected_row = full_df.loc[full_df['record_id'] == self.selected_record_id]   
        if self.selected_row.empty:
            return "", "", "", ""  # Return empty strings if no record is found
        #job_description = full_df_record['job_description']
        x = self.selected_row.iloc[0]
        return (
            self.selected_row.iloc[0]['job_description'], 
            self.selected_row.iloc[0]['tailored_resume'], 
            self.selected_row.iloc[0]['changes'],
            self.selected_row.iloc[0]['tailored_resume_filename'],
            self.selected_row.iloc[0]['job_url']
        )

    async def process_files(
        self, 
        resume_file: str, 
        excel_file:str,
        job_links_file: str, 
        job_search_type: str, 
        job_count: int,
        customer_name: str,
        customer_email: str
    ) -> str:
        """Process resume and job files."""
        jobs={}
        
        if job_search_type == "Search":
                jobs = await self.linkedin_scraper.run_job_search(job_count)
               
        else:
                jobs = get_jobs_from_excel(excel_file)
        for job in jobs:
                    self.airtable_manager.add_new_record(job, resume_file, customer_name, customer_email)
            
        new_records = self.airtable_manager.get_new_records()
        for record in new_records:
                try:
                    fields = record["fields"]
                    tailored_response = self.resume_generator.generate_tailored_resume_markdown(
                    resume_file,fields["job_title"] + "\n" + fields["job_description"]
                    )
                
                    if tailored_response!="error":
                        updated_fields = {
                        "tailored_resume": tailored_response.TailoredResume,
                        "status": "resume_generated",
                        "resume_generated_date": datetime.now().isoformat(),
                        "before": float(tailored_response.Before),
                        "after": float(tailored_response.After),
                        "changes":tailored_response.Changes,
                        "tailored_resume_filename": fields["company_name"] + "_" + fields["job_title"]
                        
                        }
                        self.airtable_manager.update_record(record["id"], updated_fields)
                except Exception as e:
                    logger.error(f"Error processing files: {str(e)}", exc_info=True)
                    return f"Error: {str(e)}"
                
        return "Process complete!"
            
        
    def create_ui(self):
        """Create and configure Gradio UI."""
        with gr.Blocks(fill_height=True) as demo:
            gr.Markdown("# Resume Tailoring Dashboard")
            
            with gr.Tabs() as tabs:
                # First Tab - Upload Section
                with gr.Tab("Upload Files"):
                    # First Row - Customer Information
                    with gr.Row():
                        with gr.Column():
                            customer_name = gr.Textbox(
                                label="Customer Name",
                                placeholder="Enter customer name"
                            )
                            customer_email = gr.Textbox(
                                label="Customer Email",
                                placeholder="Enter customer email"
                            )
                    
                    # Second Row - Split into two columns
                    with gr.Row():
                        # Left Column - Upload Controls
                        with gr.Column(scale=1):
                            pdf_input = gr.File(
                                label="Upload Resume", 
                                file_types=[".docx"]
                            )
                            excel_input = gr.File(
                                label="Upload Jobs", 
                                file_types=[".xlsx"]
                            )
                            rb_job_type = gr.Radio(
                                ["Search", "Upload"], 
                                label="Upload Job Links", 
                                value="Upload"
                            )
                            job_count = gr.Number(
                                label="Number of Jobs", 
                                value=3
                            )
                            start_button = gr.Button("Start Processing")
                        
                        # Right Column - Empty for now
                        with gr.Column(scale=1):
                            gr.Markdown("") # Placeholder
                
                # Second Tab - Dashboard Section
                with gr.Tab("Dashboard"):
                   
                    
                    with gr.Column():
                        # Top right controls row with buttons
                        with gr.Row():
                            # Add a spacer to push buttons to the right
                            gr.Markdown("")  # This creates a spacer
                            refresh_button = gr.Button(
                                "🔄", 
                                variant="secondary",
                                size="sm"
                            )
                            download_button = gr.Button("Download Resume", size="sm")
                            download_all_button = gr.Button("Download All", size="sm")
                            change_to_applied = gr.Button("Applied", size="sm")
                            # Set click events for buttons
                           
                        
                        with gr.Row():
                            full_df_state = gr.State()  # Define the state before using it
                            dashboard = gr.DataFrame(None, scale=10)  # Initialize the dashboard DataFrame
                        
                        with gr.Row():
                             clickable_url = gr.Textbox()
                        # Main content row
                        with gr.Row(scale=3):  # Increased scale for more height
                            # First column - Job Description
                            with gr.Column(scale=1):
                                job_description = gr.Textbox(
                                    label="Job Description",
                                    lines=10  # Increased lines for more content
                                )
                            
                            # Second column - Tailored Resume
                            with gr.Column(scale=1):
                                tailored_resume = gr.Textbox(
                                    label="Tailored Resume",
                                    lines=10  # Increased lines for more content
                                )
                                download_filename = gr.Textbox(
                                    label="Download File Name",
                                    visible=False
                                )
                                download_button.click(fn=save_markdowntext_to_word, inputs=[tailored_resume, download_filename], outputs=[])
                            
                            # Third column - Changes Made
                            with gr.Column(scale=1):
                                changes = gr.Textbox(
                                    label="Changes Made",
                                    lines=10  # Increased lines for more content
                                )
            refresh_button.click(fn=self.get_dashboard_data, outputs=[dashboard, full_df_state])
           
            download_all_button.click(fn=download_all_resumes)  # Implement this function

            change_to_applied.click(fn=self.update_applied_status)
            # Event handlers
            start_button.click(
                fn=self.process_files,
                inputs=[
                    pdf_input, 
                    excel_input,
                    gr.State(None), 
                    rb_job_type, 
                    job_count,
                    customer_name,
                    customer_email
                ],
                outputs=[gr.Textbox()]
            )

            dashboard.select(
                fn=self.df_select_callback,
                inputs=[full_df_state],
                outputs=[job_description, tailored_resume, changes, download_filename, clickable_url]
            )

            return demo
        
    
    def update_applied_status(self):

        if self.selected_row is not None:
            updated_fields = {
                    "status":"applied"
                        
                        }
            self.airtable_manager.update_record(self.selected_record_id, updated_fields)
            self.get_dashboard_data()
            # Call the update function with the selected row
            #self.airtable_manager.update_state_to_applied(self.selected_row)
        else:
            # Handle the case where no row is selected
            logger.warning("No row selected to update the status.")
            return "❌ No row selected to update the status."