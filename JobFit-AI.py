import openai
import json
import PyPDF2
import docx
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Utility Functions
def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def read_docx(file):
    doc = docx.Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def load_resume(uploaded_file):
    if uploaded_file.name.endswith('.pdf'):
        return read_pdf(uploaded_file)
    elif uploaded_file.name.endswith('.docx'):
        return read_docx(uploaded_file)
    else:
        st.error("Unsupported file format")
        return None

def generate_updated_resume(resume_text, match_analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()

    # Custom styles
    header_style = styles['Heading1']
    header_style.fontSize = 16
    header_style.spaceAfter = 18
    header_style.textColor = colors.HexColor('#1a1a1a')

    section_header_style = ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        spaceAfter=12,
        textColor=colors.HexColor('#0d47a1'),
        underlineWidth=1,
        underlineOffset=-3
    )

    normal_style = ParagraphStyle(
        name='NormalText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        name='BulletStyle',
        parent=normal_style,
        bulletFontName='Helvetica',
        bulletFontSize=8,
        bulletIndent=10,
        leftIndent=20
    )

    recommendation_style = ParagraphStyle(
        name='RecommendationStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#00695c'),
        leftIndent=25,
        spaceAfter=4
    )

    content = []
    content.append(Paragraph("Updated Resume", header_style))
    content.append(Spacer(1, 12))

    # Resume Content Parsing
    resume_parts = resume_text.split("\n")
    current_section = ""
    bullets = []

    def flush_bullets():
        for bullet in bullets:
            content.append(Paragraph(f"• {bullet.strip()}", bullet_style))
        bullets.clear()

    common_sections = ['EXPERIENCE', 'EDUCATION', 'SKILLS', 'PROJECTS', 'CERTIFICATIONS', 'SUMMARY', 'OBJECTIVE']

    for line in resume_parts:
        line = line.strip()
        if not line:
            continue

        is_section = line.isupper() or any(section in line.upper() for section in common_sections)

        if is_section:
            flush_bullets()
            current_section = line
            content.append(Spacer(1, 12))
            content.append(Paragraph(current_section, section_header_style))
        else:
            bullets.append(line)

    flush_bullets()

    # ATS Recommendations
    if match_analysis.get('ats_optimization_suggestions'):
        content.append(Spacer(1, 20))
        content.append(Paragraph("ATS Optimization Recommendations", section_header_style))
        content.append(Spacer(1, 10))

        for suggestion in match_analysis['ats_optimization_suggestions']:
            section = suggestion.get('section', '')
            current = suggestion.get('current_content', '')
            suggested = suggestion.get('suggested_change', '')
            keywords = ', '.join(suggestion.get('keywords_to_add', []))
            formatting = suggestion.get('formatting_suggestion', '')
            reason = suggestion.get('reason', '')

            content.append(Paragraph(f"• Section: {section}", recommendation_style))
            if current:
                content.append(Paragraph(f"  Current: {current}", recommendation_style))
            content.append(Paragraph(f"  Suggestion: {suggested}", recommendation_style))
            if keywords:
                content.append(Paragraph(f"  Keywords to Add: {keywords}", recommendation_style))
            if formatting:
                content.append(Paragraph(f"  Formatting: {formatting}", recommendation_style))
            if reason:
                content.append(Paragraph(f"  Reason: {reason}", recommendation_style))
            content.append(Spacer(1, 6))

    doc.build(content)
    buffer.seek(0)
    return buffer


def generate_updated_resume1(resume_text, match_analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Modify existing styles
    styles['Heading1'].fontSize = 14
    styles['Heading1'].spaceAfter = 16
    styles['Heading1'].textColor = colors.HexColor('#2c3e50')

    styles['Heading2'].fontSize = 12
    styles['Heading2'].spaceAfter = 12
    styles['Heading2'].textColor = colors.HexColor('#34495e')

    styles['Normal'].fontSize = 10
    styles['Normal'].spaceAfter = 8
    styles['Normal'].leading = 14

    # Add a custom style for recommendations
    styles.add(ParagraphStyle(
        name='RecommendationStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        leading=14,
        leftIndent=20,
        textColor=colors.HexColor('#2980b9')
    ))

    # Create content
    content = []

    # Add header
    content.append(Paragraph("Updated Resume", styles['Heading1']))
    content.append(Spacer(1, 12))

    # Add existing resume content with proper formatting
    resume_parts = resume_text.split("\n")
    current_section = None

    for part in resume_parts:
        if part.strip():  # Skip empty lines
            # Detect section headers (uppercase or common section names)
            common_sections = ['EXPERIENCE', 'EDUCATION', 'SKILLS', 'PROJECTS', 'CERTIFICATIONS']
            is_section = part.isupper() or any(section in part.upper() for section in common_sections)

            if is_section:
                current_section = part
                content.append(Paragraph(part, styles['Heading2']))
            else:
                content.append(Paragraph(part, styles['Normal']))
            content.append(Spacer(1, 6))

    # Add ATS optimization recommendations
    if match_analysis.get('ats_optimization_suggestions'):
        content.append(Spacer(1, 12))
        content.append(Paragraph("ATS Optimization Recommendations", styles['Heading2']))
        content.append(Spacer(1, 8))

        for suggestion in match_analysis['ats_optimization_suggestions']:
            content.append(Paragraph(f"• Section: {suggestion['section']}", styles['RecommendationStyle']))
            if suggestion.get('current_content'):
                content.append(Paragraph(f"  Current: {suggestion['current_content']}", styles['RecommendationStyle']))
            content.append(Paragraph(f"  Suggestion: {suggestion['suggested_change']}", styles['RecommendationStyle']))
            if suggestion.get('keywords_to_add'):
                content.append(Paragraph(f"  Keywords to Add: {', '.join(suggestion['keywords_to_add'])}",
                                         styles['RecommendationStyle']))
            if suggestion.get('formatting_suggestion'):
                content.append(
                    Paragraph(f"  Formatting: {suggestion['formatting_suggestion']}", styles['RecommendationStyle']))
            content.append(Spacer(1, 6))

    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer


class JobAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze_job(self, job_description: str) -> dict:
        prompt = """
        Analyze this job description and provide a detailed JSON with:
        1. Key technical skills required  
        2. Soft skills required
        3. Years of experience required
        4. Education requirements
        5. Key responsibilities
        6. Company culture indicators
        7. Required certifications
        8. Industry type
        9. Job level (entry, mid, senior)  
        10. Key technologies mentioned
        Format the response as a JSON object with these categories.
        Job Description:
        {description}
        """

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": prompt.format(description=job_description)
                }],
                temperature=0.1
            )
            parsed_response = json.loads(response.choices[0].message.content)
            return parsed_response
        except Exception as e:
            st.error(f"Error analyzing job description: {str(e)}")
            return {}

    def analyze_resume(self, resume_text: str) -> dict:
        prompt = """
        Analyze this resume and provide a detailed JSON with:
        1. Technical skills
        2. Soft skills
        3. Years of experience
        4. Education details
        5. Key achievements
        6. Core competencies  
        7. Industry experience
        8. Leadership experience
        9. Technologies used
        10. Projects completed
        Format the response as a JSON object with these categories.
        Resume:
        {resume}  
        """

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": prompt.format(resume=resume_text)
                }],
                temperature=0.1
            )
            parsed_response = json.loads(response.choices[0].message.content)
            return parsed_response
        except json.JSONDecodeError as e:
            st.error(
                f"Error parsing resume analysis response: {str(e)}. Please check the resume text for any formatting issues.")
            return {}
        except Exception as e:
            st.error(f"Error analyzing resume: {str(e)}")
            return {}

    def analyze_match(self, job_analysis: dict, resume_analysis: dict) -> dict:
        prompt = """You are a professional resume analyzer. Compare the provided job requirements and resume to generate a detailed analysis in valid JSON format.
IMPORTANT: Respond ONLY with a valid JSON object and NO additional text or formatting.
Job Requirements:
{job}

Resume Details:
{resume}

Generate a response following this EXACT structure:
{{
"overall_match_percentage":"85%",
"matching_skills":[{{"skill_name":"Python","is_match":true}},{{"skill_name":"AWS","is_match":true}}],
"missing_skills":[{{"skill_name":"Docker","is_match":false,"suggestion":"Consider obtaining Docker certification"}}],
"skills_gap_analysis":{{"technical_skills":"Specific technical gap analysis","soft_skills":"Specific soft skills gap analysis"}},
"experience_match_analysis":"Detailed experience match analysis",
"education_match_analysis":"Detailed education match analysis",
"recommendations_for_improvement":[{{"recommendation":"Add metrics","section":"Experience","guidance":"Quantify achievements with specific numbers"}}],
"ats_optimization_suggestions":[{{"section":"Skills","current_content":"Current format","suggested_change":"Specific change needed","keywords_to_add":["keyword1","keyword2"],"formatting_suggestion":"Specific format change","reason":"Detailed reason"}}],
"key_strengths":"Specific key strengths",
"areas_of_improvement":"Specific areas to improve"
}}
Focus on providing detailed, actionable insights for each field. Keep the JSON structure exact but replace the example content with detailed analysis based on the provided job and resume."""

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": prompt.format(
                        job=json.dumps(job_analysis, indent=2),
                        resume=json.dumps(resume_analysis, indent=2)
                    )
                }],
                temperature=0.2
            )
            try:
                # Clean up the response content
                response_content = response.choices[0].message.content.strip()
                # Remove any leading/trailing whitespace or quotes
                response_content = response_content.strip('"\'')
                # Parse the JSON
                parsed_response = json.loads(response_content)
                return parsed_response
            except json.JSONDecodeError as e:
                st.error(f"Error parsing match analysis response. Please try again.")
                print(f"Debug - Response content: {response.choices[0].message.content}")
                print(f"Debug - Error details: {str(e)}")
                return {}
            return parsed_response
        except Exception as e:
            st.error(f"Error analyzing match: {str(e)}")
            return {}


class CoverLetterGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_cover_letter(self, job_analysis: dict, resume_analysis: dict, match_analysis: dict,
                              tone: str = "professional") -> str:
        prompt = """
        Generate a compelling cover letter using this information:
        Job Details:
        {job}
        Candidate Details:
        {resume}
        Match Analysis:  
        {match}
        Tone: {tone}
        Requirements:
        1. Make it personal and specific
        2. Highlight the strongest matches
        3. Address potential gaps professionally  
        4. Keep it concise but impactful
        5. Use the specified tone: {tone}
        6. Include specific examples from the resume
        7. Make it ATS-friendly
        8. Add a strong call to action
        """

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": prompt.format(
                        job=json.dumps(job_analysis, indent=2),
                        resume=json.dumps(resume_analysis, indent=2),
                        match=json.dumps(match_analysis, indent=2),
                        tone=tone
                    )
                }],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating cover letter: {str(e)}")
            return ""


def main():
    st.set_page_config(page_title="RESUME ATS Assistant - JobFit-AI 📝", layout="wide")

    # API key input
    api_key = st.sidebar.text_input("Enter OpenAI API Key 🗝️", type="password")
    if not api_key:
        st.warning("🔑 Please enter your OpenAI API key to continue.")
        return

    st.title("RESUME ATS Assistant - JobFit-AI 🚀")
    st.markdown("""
    Optimize your job application by analyzing job requirements 📋, 
    matching your resume 📜, and generating tailored cover letters 💌.
    """)

    # Initialize analyzers
    job_analyzer = JobAnalyzer(api_key)
    cover_letter_gen = CoverLetterGenerator(api_key)

    # File Upload Section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Job Description 📋")
        job_desc = st.text_area("Paste the job description here", height=300)

    with col2:
        st.subheader("Your Resume 📜")
        resume_file = st.file_uploader("Upload your resume", type=['pdf', 'docx'])

    if job_desc and resume_file:
        with st.spinner("🔍 Analyzing your application..."):
            # Load and analyze resume
            resume_text = load_resume(resume_file)
            if resume_text:
                # Perform analysis
                job_analysis = job_analyzer.analyze_job(job_desc)
                resume_analysis = job_analyzer.analyze_resume(resume_text)
                match_analysis = job_analyzer.analyze_match(job_analysis, resume_analysis)

                if not job_analysis or not resume_analysis or not match_analysis:
                    st.error("Insufficient data returned from the API. Please try again.")
                    return

                # Display Results
                st.header("Analysis Results 📊")

                # Match Overview
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Overall Match 🎯",
                        f"{match_analysis.get('overall_match_percentage', '0%')}"
                    )
                with col2:
                    st.metric(
                        "Skills Match 🧠",
                        f"{len(match_analysis.get('matching_skills', []))} skills"
                    )
                with col3:
                    st.metric(
                        "Skills to Develop 📈",
                        f"{len(match_analysis.get('missing_skills', []))} skills"
                    )

                # Detailed Analysis Tabs
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "Skills Analysis 📊",
                    "Experience Match 🗂️",
                    "Recommendations 💡",
                    "Cover Letter 💌",
                    "Updated Resume 📝"
                ])

                with tab1:
                    st.subheader("Matching Skills")
                    for skill in match_analysis.get('matching_skills', []):
                        st.success(f"✅ {skill['skill_name']}")

                    st.subheader("Missing Skills")
                    for skill in match_analysis.get('missing_skills', []):
                        st.warning(f"⚠️ {skill['skill_name']}")
                        st.info(f"Suggestion: {skill['suggestion']}")

                    # Skills analysis graph
                    matching_skills_count = len(match_analysis.get('matching_skills', []))
                    missing_skills_count = len(match_analysis.get('missing_skills', []))

                    skills_data = pd.DataFrame({
                        'Status': ['Matching', 'Missing'],
                        'Count': [matching_skills_count, missing_skills_count]
                    })

                    fig = px.bar(skills_data, x='Status', y='Count', color='Status',
                                 color_discrete_sequence=['#5cb85c', '#d9534f'],
                                 title='Skills Analysis')
                    fig.update_layout(xaxis_title='Status', yaxis_title='Count')

                    st.plotly_chart(fig)

                with tab2:
                    st.write("### Experience Match Analysis 🗂️")
                    st.write(match_analysis.get('experience_match_analysis', ''))
                    st.write("### Education Match Analysis 🎓")
                    st.write(match_analysis.get('education_match_analysis', ''))

                with tab3:
                    st.write("### Key Recommendations 🔑")
                    for rec in match_analysis.get('recommendations_for_improvement', []):
                        st.info(f"**{rec['recommendation']}**")
                        st.write(f"**Section:** {rec['section']}")
                        st.write(f"**Guidance:** {rec['guidance']}")

                    st.write("### ATS Optimization Suggestions 🤖")
                    for suggestion in match_analysis.get('ats_optimization_suggestions', []):
                        st.write("---")
                        st.warning(f"**Section to Modify:** {suggestion['section']}")
                        if suggestion.get('current_content'):
                            st.write(f"**Current Content:** {suggestion['current_content']}")
                        st.write(f"**Suggested Change:** {suggestion['suggested_change']}")
                        if suggestion.get('keywords_to_add'):
                            st.write(f"**Keywords to Add:** {', '.join(suggestion['keywords_to_add'])}")
                        if suggestion.get('formatting_suggestion'):
                            st.write(f"**Formatting Changes:** {suggestion['formatting_suggestion']}")
                        if suggestion.get('reason'):
                            st.info(f"**Reason for Change:** {suggestion['reason']}")

                with tab4:
                    st.write("### Cover Letter Generator 🖊️")
                    tone = st.selectbox("Select tone 🎭",
                                      ["Professional 👔", "Enthusiastic 😃", "Confident 😎", "Friendly 👋"])

                    if st.button("Generate Cover Letter ✍️"):
                        with st.spinner("✍️ Crafting your cover letter..."):
                            cover_letter = cover_letter_gen.generate_cover_letter(
                                job_analysis, resume_analysis, match_analysis, tone.lower().split()[0])
                            st.markdown("### Your Custom Cover Letter 💌")
                            st.text_area("", cover_letter, height=400)
                            st.download_button(
                                "Download Cover Letter 📥",
                                cover_letter,
                                "cover_letter.txt",
                                "text/plain"
                            )

                with tab5:
                    st.write("### Updated Resume 📝")
                    updated_resume = generate_updated_resume(resume_text, match_analysis)

                    # Provide a download button for the updated resume
                    st.download_button(
                        "Download Updated Resume 📥",
                        updated_resume,
                        "updated_resume.pdf",
                        mime="application/pdf"
                    )


if __name__ == "__main__":
    main()