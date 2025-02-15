job_description=f"""
About the job
About Gladly:

Gladly, the customer-centered, AI-powered customer support platform is built around people, not tickets. Unlike traditional ticket-based customer support solutions, our software helps brands deliver radically personal service at scale by integrating every channel—voice, email, SMS, chat, social messaging, and self-service—into a single, lifelong conversation stream. Companies like Allbirds, Bombas, Crate & Barrel, and Warby Parker use Gladly to create exceptional customer experiences, transforming everyday customer interactions into lasting connections.



Gladly is a fully distributed company that embraces remote work and believes in flexibility, innovation, and inclusivity. We foster a collaborative, inclusive culture that prioritizes growth, DEIB, and meaningful connections. At Gladly, people are at the heart of everything we do.



We're looking for a Sr. Product Manager to join our App Platform product team, which is responsible for how developers (at Gladly, our partners, and our customers) connect critical systems into the Gladly product. This PM will also be thinking about the experience that customer service agents (we call them heroes!) have when interacting with consumers using Gladly. This experience covers understanding who the customer is, including important context on their purchases and other helpful information, the lifelong conversation they've had across all channels, and ways to take action to address customers' needs. The team also thinks about how heroes collaborate with other teammates, and the role of AI in helping automate the simple stuff so they can focus on more complex and empathetic work. Our product teams are led by a product manager, designer, and engineering manager, and are organized around personas, which helps us create a long-term vision and build toward that.



We draw inspiration from consumer apps and messaging experiences, and because we have all communication channels in one platform, we have shifted what consumers can expect from companies. And with a range of powerful AI features, we are pioneering how to balance the ease and scale of automation with the empathy and intuition of heroes. This is a great opportunity to work on an experience that people use all day to help create great experiences for millions of people.



We'd ideally find a new teammate who can grasp technical and design concepts to bring out the best in their teammates, takes complex problems and guides towards simple and intuitive solutions, can sift out the signal from the noise, and is excited to collaborate with customers, stakeholders, and other teams to drive impact.



What you'll do on the team:

Create a vision and strategy for your product area that furthers the company goals and vision
Deeply understand the market and customer needs to identify compelling problems worth solving and the viability of solutions, in partnership with design, marketing, and engineering
Validate, plan, and deliver on both impactful enhancements and new products
Collaborate across Product teams to build a cohesive product and hone your PM craft
Bring others along in the process (Sales, Customer Success, Execs, partners, etc.), and align teams with a clear message


A few projects you could be working on:

Making it easier for heroes to get up to speed when starting to help a customer
Understanding the ecosystem of tools that heroes use outside Gladly, and collaborating with Partnerships to unlock key areas of opportunity
Exploring and articulating a vision for how heroes can collaborate with each other and AI to deliver service that makes customers feel known and appreciated


What you'll bring to the team:

Have 5+ years of experience as a product manager, preferably with some exposure in B2B SaaS and products for superusers
Demonstrate strong communication skills and intuition for how to approach communication with a wide range of audiences
Can telescope between the details and the big picture
Are skilled at discovery, gathering, and navigating qualitative and quantitative inputs
Know what great design looks like, and care about delivering experiences modern consumers will enjoy
Grasp technical details and understand technical constraints when working with engineers
Build trust easily with collaborators and listen well, while also knowing how to push forward independently where needed
Love tackling hard problems and coming up with powerfully simple solutions
"""


import autogen
from autogen import AssistantAgent, UserProxyAgent
import config
from utils import get_wordfile_markdown, get_resume_text
from prompts import TAILORING_PROMPT


class AgentFramework:
    def __init__(self, resume_text, job_description) -> None:
        self.resume_text = resume_text
        self.job_description = job_description
        self.tailoring_prompt = TAILORING_PROMPT.format(
            job_description=self.job_description,
            resume_text=self.resume_text)
        self.review_prompt = """You will receive the tailored resume and job description from user proxy agent.
        This is the tailored resume that you need to review against the job description.
    1. Compare the tailored resume to job profile. What is the ATS match compatibility?
    2. Does the tailored resume contain the key skills and keywords from the job profile?
    3. Does the tailored resume introduce fabricated data?
    4. Provide improvement suggestions to enhance the resume's alignment with the job profile.
    5. Send these suggestions to the ResumeGeneratorAgent for revision.
    """

    # LLM Configuration
    config_list_gemini = autogen.config_list_from_json(
        env_or_file="OAI_CONFIG_LIST.json",
        filter_dict={"model": ["gemini-pro"]}
    )

    config_list_claude= autogen.config_list_from_json(
        env_or_file="OAI_CONFIG_LIST.json",
        filter_dict={"model": ["claude-3-sonnet"]}
    )

    llm_config_gemini = {
        "config_list": config_list_gemini,
        "timeout": 120,
    }

    llm_config_claude = {
        "config_list": config_list_claude,
        "timeout": 120,
    }

    def agent_setup(self):

        self.resumeReviewerAgent = AssistantAgent(
            name="resumeReviewerAgent",
            system_message="I am a competent resume analyzer. I will review the tailored resume and provide structured feedback. Return 'TERMINATE' when done.",
            llm_config=AgentFramework.llm_config_gemini
        )

        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
            human_input_mode="NEVER",
            max_consecutive_auto_reply=2,
            code_execution_config=False,
            llm_config=AgentFramework.llm_config_gemini
        )
        self.resumeGeneratorAgent = AssistantAgent(
                name="ResumeGeneratorAgent",
                system_message=self.tailoring_prompt,
                llm_config=AgentFramework.llm_config_gemini
            )

    def initiate_process(self):
        """Initialize the conversation flow between agents."""
        
        # First, get the initial tailored resume from resumeGeneratorAgent
        response = self.user_proxy.initiate_chat(
            recipient=self.resumeGeneratorAgent,
            messages=[{"role": "user", "content": self.tailoring_prompt}],
            clear_history=True,
            silent=False
        )

        # Get the content from the response
        tailored_resume = response.last_message()['content']  # Use last_message() to get the content

        # Now send to reviewer with both resume and job description
        review_message = f"""
        {self.review_prompt}

        Resume:
        {tailored_resume}

        Job Description:
        {self.job_description}
        """

        # Send to reviewer
        review_response = self.user_proxy.initiate_chat(
            recipient=self.resumeReviewerAgent,
            messages=[{"role": "user", "content": review_message}],
            clear_history=True,
            silent=False
        )

        # Process the review response
        review_feedback = review_response.last_message().get('content', '').strip()

        iteration = 0
        max_iterations = 1 # Limit iterations to avoid infinite loops


        while iteration < max_iterations:
            if "TERMINATE" in review_feedback or not review_feedback:
                print("Final resume achieved. Stopping process.")
                break

            # Send feedback to the resume generator for revision
            response = self.user_proxy.initiate_chat(
                recipient=self.resumeGeneratorAgent,
                messages=[{"role": "user", "content": f"Revise the resume based on this feedback:\n\n{review_feedback}"}],
                clear_history=True,
                silent=False
            )

            iteration += 1

        print("Process completed after iterations:", iteration)


# Sample Job Description and Resume Input
 # Use actual job description here
#resume_text = get_wordfile_markdown("Mahesh_Resume.docx")
resume_text = get_resume_text("resume.pdf")
# Initialize and Start the Process
agent = AgentFramework(resume_text=resume_text, job_description=job_description)
agent.agent_setup()
agent.initiate_process()
