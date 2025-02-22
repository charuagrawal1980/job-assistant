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
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import PromptTemplate
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')#class TailoredResume(BaseModel):
    #desc: dict[str, str]
class TailoredResume(BaseModel):
    Before: Decimal
    After: Decimal
    Changes: str
    TailoredResume: str

response_schemas = [
    ResponseSchema(name="Before", description="Match score before tailoring (0-1)", type="float"),
    ResponseSchema(name="After", description="Match score after tailoring (0-1)", type="float"),
    ResponseSchema(name="Changes", description="List of changes made to the resume"),
    ResponseSchema(name="TailoredResume", description="The complete tailored resume")
]
parser = StructuredOutputParser.from_response_schemas(response_schemas)
@CrewBase
class LatestAiDevelopmentCrew():

  def __init__(self, resume_text, job_description):
     self.resume_text = resume_text
     self.job_description = job_description

  agents_config = "config/agents.yaml"
  tasks_config = 'config/tasks.yaml' 
  max_iterations = 2
  #os.environ["GEMINI_API_KEY"] = "AIzaSyDG_ROaq2XsXkUnSrbwl6Q8A56-M3ycRyo"
  gemini_llm = LLM(
       model="gemini/gemini-2.0-flash",
       google_api_key="AIzaSyDG_ROaq2XsXkUnSrbwl6Q8A56-M3ycRyo",
       #max_tokens=8192
       
   )
  #gemini_llm = LLM(
   # model="gpt-4o-mini",
   # api_key="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"
  #)
  #gemini_llm = LLM(
   # model="openrouter/deepseek/deepseek-r1",
   # base_url="https://openrouter.ai/api/v1",
   #api_key="sk-85d910d9206e403c8ed5ff45b87b08f8"
  #)
 
  @agent
  def resume_tailor_manager(self) -> Agent:
    format_instructions = parser.get_format_instructions()
    return Agent(
      config=self.agents_config['resume_tailor_manager'],
      verbose=False,
      llm=LatestAiDevelopmentCrew.gemini_llm,
      system_message=f"""
            You must provide your response in the following format:
            {format_instructions}
            """,
            output_parser=parser,
            max_iter=LatestAiDevelopmentCrew.max_iterations
    )
  
  @agent
  def resume_reviewer(self) -> Agent:
    return Agent(
      config=self.agents_config['resume_reviewer'],
      verbose=True,
      llm=LatestAiDevelopmentCrew.gemini_llm,
      max_iter=LatestAiDevelopmentCrew.max_iterations
    )
  

  @agent
  def final_resume_generator(self) -> Agent:
    
    format_instructions = parser.get_format_instructions()
    return Agent(
      config=self.agents_config['final_resume_generator'],
      verbose=True,
      #output_pydantic=TailoredResume,
       system_message=f"""
        You must provide your response in the following format:
        {format_instructions}
        Important: Do not include any additional text or formatting before and after the JSON response. The only output should be a valid JSON.
        """,
        output_parser=parser.parse,  # Use the structured parser
        llm=LatestAiDevelopmentCrew.gemini_llm,
        max_iter=LatestAiDevelopmentCrew.max_iterations
     
    )
  
  @agent
  def skills_tailor(self) -> Agent:
    return Agent(
        config=self.agents_config['skills_tailor'],
        verbose=True,
        llm=LatestAiDevelopmentCrew.gemini_llm,
        max_iter=LatestAiDevelopmentCrew.max_iterations
    )

  @agent
  def professional_experience_tailor(self) -> Agent:
    return Agent(
        config=self.agents_config['professional_experience_tailor'],
        verbose=True,
        llm=LatestAiDevelopmentCrew.gemini_llm,
        max_iter=LatestAiDevelopmentCrew.max_iterations
    )

  @task
  def tailor_skills_task(self) -> Task:
    return Task(
        config=self.tasks_config['tailor_skills_task'],
        agent=self.skills_tailor(),
        inputs={
            "resume_text": self.resume_text,
            "job_description": self.job_description
        }
    )

  @task
  def tailor_professional_experience_task(self) -> Task:
    skills_task = self.tailor_skills_task()
    return Task(
        config=self.tasks_config['tailor_professional_experience_task'],
        agent=self.professional_experience_tailor(),
        context=[self.tailor_skills_task()],
      
    )

  @task
  def resume_manager_task(self) -> Task:
    return Task(
      config=self.tasks_config['resume_manager_task'],
      agent=self.resume_tailor_manager(),
      context=[self.tailor_skills_task(),self.tailor_professional_experience_task()]
    )

  @task
  def resume_review_task(self) -> Task:
    return Task(
      config=self.tasks_config['resume_review_task'],
      context=[self.resume_manager_task()],
      agent=self.resume_reviewer()
      #output_from_resume_tailor_task="{context[0]}"
    )

  @task
  def final_resume_generator_task(self) -> Task:
    return Task(
      config=self.tasks_config['final_resume_generator_task'],
      context=[self.resume_review_task(), self.resume_manager_task()],
      agent=self.final_resume_generator()
      )
  
  #@before_kickoff
  #def prepare_inputs(self, inputs):
        # Modify inputs before the crew starts
        # resume_text = self.resume_text #LatestAiDevelopmentCrew.get_resume_text("resume.pdf")
        # job_description = self.job_description #  LatestAiDevelopmentCrew.get_job_description("jobs.txt")
        # logger.info(f"Inputs:{inputs}")
        # inputs['resume_text'] = resume_text
        # inputs['job_description'] = job_description
        # return inputs

  # @after_kickoff
  # def process_output(self, output):
  #     # Modify output after the crew finishes
  #     output.raw += "\nProcessed after kickoff."
  #     return output

  @crew
  def crew(self) -> Crew:
    return Crew(
      agents=[
        self.skills_tailor(),
        self.professional_experience_tailor(),
        self.resume_tailor_manager(),
        #self.resume_reviewer(),
        #self.final_resume_generator()
      ],
      tasks=[
        self.tailor_skills_task(),
        self.tailor_professional_experience_task(),
        self.resume_manager_task(),
        #self.resume_review_task(),
        #self.final_resume_generator_task()
      ],
      process=Process.sequential,
      #memory=True,
    verbose=True
    
    )
