from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from langchain_google_genai import ChatGoogleGenerativeAI
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
import pdfplumber
import litellm
import os
from pydantic import BaseModel
from decimal import Decimal

#class TailoredResume(BaseModel):
    #desc: dict[str, str]
class TailoredResume(BaseModel):
    Before: Decimal
    After: Decimal
    Changes: str
    TailoredResume: str
@CrewBase
class LatestAiDevelopmentCrew():

  def __init__(self, resume_text, job_description):
     self.resume_text = resume_text
     self.job_description = job_description

  agents_config = "config/agents.yaml"
  tasks_config = 'config/tasks.yaml' 
 
  os.environ["GEMINI_API_KEY"] = "AIzaSyDG_ROaq2XsXkUnSrbwl6Q8A56-M3ycRyo"
  gemini_llm = LLM(
       model="gemini/gemini-pro",
       google_api_key="AIzaSyDG_ROaq2XsXkUnSrbwl6Q8A56-M3ycRyo"
       
   )

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
        #logger.error(f"Error extracting resume text: {str(e)}", exc_info=True)
        return ""

  def get_job_description(job_description_filename: str) -> str:
    with open(job_description_filename, "r") as file:
        return file.read()
  @agent
  def resume_generator(self) -> Agent:
    return Agent(
      config=self.agents_config['resume_generator'],
      verbose=False,
      llm=LatestAiDevelopmentCrew.gemini_llm
    )
  
 

  @agent
  def resume_reviewer(self) -> Agent:
    return Agent(
      config=self.agents_config['resume_reviewer'],
      verbose=True,
      llm=LatestAiDevelopmentCrew.gemini_llm
    )

  @agent
  def final_resume_generator(self) -> Agent:
    return Agent(
      config=self.agents_config['final_resume_generator'],
      verbose=True,
      output_pydantic=TailoredResume,
      llm=LatestAiDevelopmentCrew.gemini_llm
     
    )
  
  @task
  def resume_tailor_task(self) -> Task:
    return Task(
      config=self.tasks_config['resume_tailor_task']
    )


  @task
  def resume_review_task(self) -> Task:
    return Task(
      config=self.tasks_config['resume_review_task'],
      context=[self.resume_tailor_task()],
      #output_from_resume_tailor_task="{context[0]}"
    )

  @task
  def final_resume_generator_task(self) -> Task:
    return Task(
      config=self.tasks_config['final_resume_generator_task'],
      context=[self.resume_review_task()]
      #output_from_resume_review_task="{context[0]}"
      )
  
  @before_kickoff
  def prepare_inputs(self, inputs):
        # Modify inputs before the crew starts
        resume_text = self.resume_text #LatestAiDevelopmentCrew.get_resume_text("resume.pdf")
        job_description = self.job_description #  LatestAiDevelopmentCrew.get_job_description("jobs.txt")
        inputs['resume_text'] = resume_text
        inputs['job_description'] = job_description
        return inputs

  @after_kickoff
  def process_output(self, output):
        # Modify output after the crew finishes
        output.raw += "\nProcessed after kickoff."
        return output

  @crew
  def crew(self) -> Crew:
    return Crew(
      agents=[
        self.resume_generator(),
        self.resume_reviewer(),
        self.final_resume_generator()
      ],
      tasks=[
        self.resume_tailor_task(),
        self.resume_review_task(),
        self.final_resume_generator_task()
      ],
      process=Process.sequential
    )
