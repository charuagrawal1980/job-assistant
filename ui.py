import gradio as gr
import pandas as pd
from typing import Tuple
import logging
from datetime import datetime
from prompts import Prompts
from utils import save_resume_to_pdf, save_markdowntext_to_word, download_all_resumes
from utils import get_jobs_from_excel


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

isSheets=True

class GradioUI:
    full_df_state: pd.DataFrame
    selected_row: gr.SelectData
    selected_record_id: str
    customer_email :str

    def __init__(self, airtable_manager, linkedin_scraper, resume_generator, prompts, sheet_manager):
        """Initialize Gradio UI components."""
        self.airtable_manager = airtable_manager
        self.linkedin_scraper = linkedin_scraper
        self.resume_generator = resume_generator
        self.sheet_manager = sheet_manager
        self.selected_row = None
        self.customer_email = None
        self.prompts = prompts
    
    def get_records(self):
        records=None
        if (isSheets):
            if self.customer_email is None or len(self.customer_email)==0:
                return self.sheet_manager.get_all_records()
            else:
                 records = self.sheet_manager.get_all_records_by_customer(self.customer_email)
        else:
            if self.customer_email is None or len(self.customer_email)==0:
                records = self.airtable_manager.get_all_records()
            else:
                 records = self.airtable_manager.get_all_records_by_customer(self.customer_email)
        return records

    def get_data_for_dataframe(self,records):
        df = pd.DataFrame(columns=[
                'record_id','customer_name', 'customer_email_address', 'job_title', 'job_url','resume_generated_date', 'original_resume','company_name',
                'status', 'tailored_resume', 'before','after','changes', 'tailored_resume_filename', 'created_date', 
                'job_description'
            ])
        if(isSheets):
            
            for record in records:
                df.loc[len(df)] = record
        else:
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
        return df
    
    def get_dashboard_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
       
        try:
            
            records = self.get_records()
            df= self.get_data_for_dataframe(records)
            # Create display DataFrame with hidden columns
            display_df = df[['company_name', 'job_title', 'job_url', 'before','after', 
                           'status', 'created_date', 'record_id']]
            
            return display_df, df
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
            return pd.DataFrame(), pd.DataFrame()

    def df_select_callback(self, full_df: pd.DataFrame, evt: gr.SelectData) -> Tuple[str, str, str, str]:
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

    def add_job_profile_records(self,job, resume_file, customer_name, customer_email):
        if(isSheets):
                self.sheet_manager.add_new_record(job, resume_file, customer_name, customer_email)
        else:
                 self.airtable_manager.add_new_record(job, resume_file, customer_name, customer_email)


    def get_records_for_tailoring(self):
         if (isSheets):
            return self.sheet_manager.get_all_records_for_tailoring()
         else:
            return self.airtable_manager.get_new_records()
    
    def generate_tailored_resume(self,record, resume_file):
         if(isSheets):
            tailored_response = self.resume_generator.generate_tailored_resume_markdown(resume_file,
                                                                                        record["job_title"] + "\n" + record["job_description"], self.prompts)
               
         else:
            fields = record["fields"]
            tailored_response = self.resume_generator.generate_tailored_resume_markdown(resume_file,
                                                                                        fields["job_title"] + "\n" + fields["job_description"], self.prompts
                    )
            return tailored_response

    def get_file_name_for_tailored_resume(self,record):   
        if (isSheets):
         return record["company_name"] + "_" +  record["job_title"]
        else:
            row = record["fields"]
            return row["company_name"] + "_" + row["job_title"]

    def update_tailored_resume(self,record, updated_fields):
        if(isSheets):
            self.sheet_manager.update_record(record["record_id"],updated_fields)
        else:
            self.airtable_manager.update_record(record["record_id"], updated_fields)
  
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
        
        if len(customer_email)==0:
             raise gr.Error("You need to enter a valid email address") 
        if (resume_file is None):
            raise gr.Error("You need to upload a .docx resume file")
        if(excel_file is None):
             raise gr.Error("You need to upload an excel file with jobs. Contact Job Assitant team for the template if you don't have one")
        
        gr.Info(f"""It might take a few mins to generate tailored resumes"\n
                "You will see 'Process Complete' on the screen and then you can refresh the dashboard""")
        self.customer_email = customer_email
        logger.info("Starting the process for email:" + self.customer_email)
        jobs={}
        
        if job_search_type == "Search":
                jobs = await self.linkedin_scraper.run_job_search(job_count)
               
        else:
                
                logger.info("Calling excel file to get jobs")
                jobs = get_jobs_from_excel(excel_file)
                logger.info("Got all excel jobs. Total Job Count:" + str(len(jobs)))
        for job in jobs:
                self.add_job_profile_records(job, resume_file, customer_name, customer_email)
                  
        logger.debug("Finished adding all original resume records to table:" + str(len(jobs)))    
        new_records = self.get_records_for_tailoring()
        #new_records = self.airtable_manager.get_new_records()
        count=1
        for record in new_records:
                try:
                    
                    #fields = record["fields"]
                    logger.info("Generating tailored resume for Count:{}".format(count)) 
                    if(isSheets):
                        job_description =record['job_description']
                    else:
                         fields = record["fields"]
                         job_description = fields["job_description"]
                    tailored_response = self.resume_generator.generate_tailored_resume_markdown(resume_file, job_description, self.prompts)
                    #tailored_response = self.resume_generator.generate_tailored_resume_markdown(
                    #resume_file,fields["job_title"] + "\n" + fields["job_description"], self.prompts
                    #)
                    logger.info("Finished generating tailored resume for job title:") 
                    if tailored_response!="error":
                        updated_fields = {
                        "tailored_resume": tailored_response['TailoredResume'],
                        "status": "resume_generated",
                        "resume_generated_date": datetime.now().isoformat(),
                        "before": float(tailored_response['Before']),
                        "after": float(tailored_response['After']),
                        "changes":tailored_response['Changes'],
                        "tailored_resume_filename": self.get_file_name_for_tailored_resume(record) #fields["company_name"] + "_" + fields["job_title"]
                        
                        }
                        #logger.info("updating job title:{} record id:{}".format(record["id"], fields["job_title"]))
                        self.update_tailored_resume(record, updated_fields)
                        #self.airtable_manager.update_record(record["id"], updated_fields)
                        #logger.info("Finished updating job title:{1} record id:{0}".format(record["id"], fields["job_title"]))
                        count+=1
                except Exception as e:
                    logger.error(f"Error processing files: {str(e)}", exc_info=True)
                    return f"Error: {str(e)}"
        logger.info("Process complete for email address:" + self.customer_email)        
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
                            customer_email.change(fn=self.customer_changed, inputs=[customer_email])
                    
                    # Second Row - Split into two columns
                    with gr.Row():
                        # Left Column - Upload Controls
                        with gr.Column(scale=1):
                            pdf_input = gr.File(
                                label="Upload Resume", 
                                file_types=[".docx"], interactive=True, height=50
                            )
                            excel_input = gr.File(
                                label="Upload Jobs", 
                                file_types=[".xlsx"],interactive=True, height=50
                            )
                            
                            rb_job_type = gr.Radio(
                                ["Search", "Upload"], 
                                label="Upload Job Links", 
                                value="Upload", visible=False
                            )
                            job_count = gr.Number(
                                label="Number of Jobs", 
                                value=3, visible=False
                            )
                            
                            start_button = gr.Button("Start Processing")
                            status_output = gr.Textbox(label="Status", interactive=False, visible=True)
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
                            refresh_button = gr.Button("🔄", variant="secondary", size="sm", elem_id="refresh-button")
                            download_button = gr.Button("Download Resume", size="sm", elem_id="download-button")
                            change_to_applied = gr.Button("Change to Applied", size="sm", elem_id="apply-button")
                            tailored_resume_pdf = gr.File(label="Download Tailored Resume", visible=True, interactive=True, height=30)
                        with gr.Row():
                             full_df_state = gr.State()  # Define the state before using it
                             dashboard = gr.DataFrame(None, scale=10)  # Initialize the dashboard DataFrame
                        with gr.Row():
                             clickable_url = gr.Textbox()
                        with gr.Row(scale=3):  # Increased scale for more height
                            job_description = gr.Textbox(label="Job Description", lines=10)
                            tailored_resume = gr.Textbox(label="Tailored Resume", lines=10)
                            download_filename = gr.Textbox(label="Download File Name", visible=False)
                            changes = gr.Textbox(label="Changes Made", lines=10)
                        #with gr.Row():
                         #   tailored_resume_pdf = gr.File(label="Download Tailored Resume", visible=True, height=10)
                    
                with gr.Tab("Tailoring Prompt"):
                     prompt_textbox = gr.TextArea(label="Tailoring prompt", value =self.prompts.get_tailoring_prompt(), 
                                         interactive=True, lines=15)
                     update_prompt_button = gr.Button("Update Prompt")
                     update_prompt_button.click(
                    fn=self.prompts.update_tailoring_prompt,  # Update the prompt in the Prompts class
                    inputs=[prompt_textbox],  # Input from the textbox
                    outputs=[]  # No output needed
                )
                with gr.Tab("Read me"):
                        gr.Markdown(f"""Detailed Instructions:
                        1. Upload your resume in docx format 
                        2. Upload the job template file. This template file has job title, company name, job link and job description. If you do not have this template, reach out to the job assitant team.
                        3. Make sure you have entered your email address and then click Start Processing.
                        4. This step uses AI to generate tailiored resumes for each of the job profile.
                        5. Depending on number of entries in the job template, this might take 3-5 minutes for 10 jobs.
                        5. Wait until the Process is complete. You will see the status text update to 'Process complete'
                        5. Go to the dashboard and click Refresh icon on the top. If you have an email address on the first tab, dashboard will only list records for that email address,
                            else it will list all job profiles in the system. If you want to see only your jobs, make sure to enter the correct email address on the first tab.
                        6. You can select a row in the grid to see the job description, tailored resume and the changes made to original resume
                        7. You can download the tailored resume on your local by clicking on 'Download' button and start applying with it.
                        8. Once you have completed applying for the job, select the job profile on grid that you have applied for and click on button 'Change to Applied'. Refresh the grid and the state 
                            is changed to applied. This will help you keep track of the process.
                        """)
                       
                        start_button.click(
                            fn=self.process_files,  # Your processing function
                            inputs=[
                                pdf_input, 
                                excel_input,
                                gr.State(None), 
                                rb_job_type, 
                                job_count,
                                customer_name,
                                customer_email
                            ],
                            outputs=[status_output],  # Include the file output
                            show_progress=True  # Show progress bar
                        )
                        refresh_button.click(fn=self.get_dashboard_data, outputs=[dashboard, full_df_state])
                        download_button.click(fn=save_markdowntext_to_word, inputs=[tailored_resume, download_filename], outputs=[tailored_resume_pdf])
                        change_to_applied.click(fn=self.update_applied_status)  # Call the update function
                        dashboard.select(
                fn=self.df_select_callback,
                inputs=[full_df_state],
                outputs=[job_description, tailored_resume, changes, download_filename, clickable_url])
                change_to_applied.click(fn=self.update_applied_status)
            

            # Custom CSS to adjust button sizes
            demo.css = """
            #refresh-button, #download-button, #apply-button {
                width: 60px;  /* Set a smaller width */
                height: 40px;  /* Increase height */
            }
            """

            return demo
        
    def customer_changed(self,email):
         self.customer_email = email

    def get_records_created_today(self, email):
        return ""
    def update_applied_status(self):

        if self.selected_row is not None:
            updated_fields = {
                    "status":"applied"
                        
                        }
            if(isSheets):
                self.sheet_manager.update_record(self.selected_record_id, updated_fields)
            else:
                self.airtable_manager.update_record(self.selected_record_id, updated_fields)
            self.get_dashboard_data()
           
        else:
            # Handle the case where no row is selected
            logger.warning("No row selected to update the status.")
            return "❌ No row selected to update the status."