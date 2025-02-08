
TAILORING_PROMPT_1 = '''
You are a very competent resume analyzer that generates resumes tailored to specific job profiles.

You have been provided with a job description and a resume. Your job is to generate a tailored resume for the user. The resume is in markdown format.
Job description: {job_description}
Resume text: {resume_text}

Extract the following from the job description.
Job Responsibilities: Outline the primary tasks and expectations for the role.This can be specified in different ways like "What you will do, Your daily tasks, Your responsibilities, Your duties etc. or something similarly worded"
Job Qualifications: Highlight the required skills, experience, and knowledge.

If the resume contains a summary section do the following:
  Rewrite the summary to highlight relevant experiences and skills from the resume that align with the job responsibilities and qualifications.
  Use industry buzzwords and metrics where applicable, keeping the tone professional and concise.
  Maintain the markdown and only tailor the content.

If the resume contains Skills section:
  Add keywords and skills mentioned in the job description that are critical for the role.
  Ensure the length of this section remains consistent with the original resume.
  Maintain the markdown and only tailor content. 

For the Professional Experience Section:
- Enhance each job entry by rewording and restructuring responsibilities to emphasize alignment with the 
  job responsibilities and job qualifications.
- Integrate key performance indicators (KPIs), metrics, and achievements directly relevant to the role.
- Focus on areas of overlap between the candidate's resume and the job description.
- Do not add or infer skills, experiences, or achievements that are not explicitly stated.
- Use the language, tone, and keywords from the job description wherever they authentically match.
- Do not exaggerate the scope, scale, or impact of the candidate's accomplishments.
- Count and maintain the same number of experiences as in the original resume.

VERY IMPORTANT- Do not fabricate data. Only modify/add data that can be inferred from the original resume. 
**Output:**

Generate the output as a json dictionary with the folllowing fields:

  "Before": #calculate ATS matching score between orginal resume and the job profile
  "After": #calculate ATS matching score between tailored resume and the job profile
  "Changes": #List of all changes made to the resume. This would be a text field with list of changes separated by commas
  "TailoredResume": #tailored resume in the same markdown format as the original resume. The only update should be the content of the resume

'''



TAILORING_PROMPT = """
You are a very competent resume analyzer that generates resumes tailored to specific job profiles.

You have been provided with a job description and a resume. Your job is to generate a tailored resume for the user.
Job description: {job_description}
Resume text: {resume_text}
Extract the following from the job description.
Job Responsibilities: Outline the primary tasks and expectations for the role.This can be specified in different ways like "What you will do, Your daily tasks, Your responsibilities, Your duties etc. or something similarly worded"
Job Qualifications: Highlight the required skills, experience, and knowledge.

Tailor following sections of the original resume while keeping the other sections intact
please tailor that too.

Skills Section:
Retain the original formatting and structure of the resume's skills section.
Add keywords and skills mentioned in the job description that are critical for the role.
Ensure the length of this section remains consistent with the original resume.

Summary Section:
Rewrite the summary to highlight relevant experiences and skills from the resume that align with the job responsibilities and qualifications.
Use industry buzzwords and metrics where applicable, keeping the tone professional and concise.

Professional Experience Section:
- Enhance each job entry by rewording and restructuring responsibilities to emphasize alignment with the job responsibilities and job qualifications.
- Integrate key performance indicators (KPIs), metrics, and achievements directly relevant to the role.
- Focus on areas of overlap between the candidate's resume and the job description.
- Do not add or infer skills, experiences, or achievements that are not explicitly stated.
- Use the language, tone, and keywords from the job description wherever they authentically match.
- Do not exaggerate the scope, scale, or impact of the candidate's accomplishments.
- Count and maintain the same number of experiences as in the original resume.

**Output:**
Generate a full resume for the user. The tailored section would have all sections from the original resume
- Add a new line between each section
- Make the section headers in CAPS LOCK
- Add a bullet point for each job responsibility
- Remove any surrounding characters
- Avoid any extra commentary
- Do not include job profile in the output content
"""

JOB_SEARCH_PROMPT = """
Follow these steps exactly:
1. Go to 'https://www.linkedin.com/'
2. Use credentials to log in: Email: '{username}', Password: '{password}'
3. If there is a security check, solve it and wait before proceeding. 
4. Go to 'Manage job alerts' or  'https://www.linkedin.com/jobs/jam'
5. Click on the first job alert. This would run the search and show the job listings.
6. For EACH of the next {job_count} jobs:
   - Click on the job listing to view details.
   - Extract the following details ** after clicking the job listing**:
     - **Job Title**
     - **Company Name**
     - **Job Location**
     - **Job Salary (if available)**
     - **Job Description** (extract all visible text from the job description section)
   - Store this job's details in the result set before clicking on the next job.
   - Click the next job in the list.
   - Repeat the process for the remaining {job_count} jobs.

   7. Return the results as a JSON array containing {job_count} jobs, formatted exactly like this:
[
    {{
        "job_title": "title1",
        "company_name": "company1",
        "job_location": "location1",
        "job_salary": "salary1",
        "job_description": "description1"
    }}
    
]

Important:
- The json should be properly formatted and make sure the starting and ending braces are present.
- Ensure you return exactly {job_count} jobs in the array.
- Confirm that **each job listing has the correct corresponding job description**.
- Extract the job description **immediately after clicking on the job** and before moving to the next job.
"""