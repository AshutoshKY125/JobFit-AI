from __future__ import annotations

import os
import json
from io import BytesIO
from typing import Any, Dict

import google.generativeai as genai
import PyPDF2
import docx
import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

SUPPORTED_MODELS = [
    "models/gemini-2.0-flash",
    "models/gemini-pro",
]

class LLMClient:
    def __init__(self, api_key: str, model_name: str = "models/gemini-2.0-flash", temperature: float = 0.2):
        if not api_key:
            raise ValueError("Missing Gemini API key")
        genai.configure(api_key=api_key)
        if model_name not in SUPPORTED_MODELS:
            model_name = SUPPORTED_MODELS[0]
        self.model_name = model_name
        self.temperature = float(temperature)
        self.model = genai.GenerativeModel(model_name)

    def _first_text(self, response) -> str:
        try:
            return (response.text or "").strip()
        except Exception:
            try:
                return "\n".join(
                    part.text for cand in response.candidates for part in cand.content.parts if getattr(part, "text", None)
                ).strip()
            except Exception:
                return ""

    def generate_text(self, prompt: str, temperature: float | None = None) -> str:
        cfg = genai.types.GenerationConfig(temperature=self.temperature if temperature is None else float(temperature))
        resp = self.model.generate_content(prompt, generation_config=cfg)
        return self._first_text(resp)

    def generate_json(self, prompt: str, temperature: float | None = None) -> Dict[str, Any]:
        raw = self.generate_text(prompt, temperature)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{[\s\S]*\}$", raw) or re.search(r"\{[\s\S]*\}", raw)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {}


def read_pdf(file) -> str:
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        try:
            text += page.extract_text() or ""
        except Exception:
            continue
    return text


def read_docx(file) -> str:
    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs)


def load_resume(uploaded_file):
    if uploaded_file.name.lower().endswith(".pdf"):
        return read_pdf(uploaded_file)
    if uploaded_file.name.lower().endswith(".docx"):
        return read_docx(uploaded_file)
    st.error("Unsupported file format please upload a PDF or DOCX")
    return None

# =============================
# PDF export helpers
# =============================

def generate_updated_resume(resume_text, match_analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    header_style = styles["Heading1"]
    header_style.fontSize = 16
    header_style.spaceAfter = 18
    header_style.textColor = colors.HexColor("#1a1a1a")

    section_header_style = ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        spaceAfter=12,
        textColor=colors.HexColor("#0d47a1"),
        underlineWidth=1,
        underlineOffset=-3,
    )

    normal_style = ParagraphStyle(
        name="NormalText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        name="BulletStyle",
        parent=normal_style,
        bulletFontName="Helvetica",
        bulletFontSize=8,
        bulletIndent=10,
        leftIndent=20,
    )

    recommendation_style = ParagraphStyle(
        name="RecommendationStyle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#00695c"),
        leftIndent=25,
        spaceAfter=4,
    )

    content = []
    content.append(Paragraph("Updated Resume", header_style))
    content.append(Spacer(1, 12))

    resume_parts = [line.strip() for line in resume_text.splitlines() if line.strip()]
    bullets = []

    def flush_bullets():
        for bullet in bullets:
            content.append(Paragraph(f"â€¢ {bullet}", bullet_style))
        bullets.clear()

    common_sections = {"EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "CERTIFICATIONS", "SUMMARY", "OBJECTIVE"}

    for line in resume_parts:
        is_section = line.isupper() or any(section in line.upper() for section in common_sections)
        if is_section:
            flush_bullets()
            content.append(Spacer(1, 12))
            content.append(Paragraph(line, section_header_style))
        else:
            bullets.append(line)
    flush_bullets()

    # ATS Recommendations
    suggestions = (match_analysis or {}).get("ats_optimization_suggestions", [])
    if suggestions:
        content.append(Spacer(1, 20))
        content.append(Paragraph("ATS Optimization Recommendations", section_header_style))
        content.append(Spacer(1, 10))
        for s in suggestions:
            section = s.get("section", "")
            current = s.get("current_content", "")
            suggested = s.get("suggested_change", "")
            keywords = ", ".join(s.get("keywords_to_add", []) or [])
            formatting = s.get("formatting_suggestion", "")
            reason = s.get("reason", "")
            content.append(Paragraph(f"â€¢ Section: {section}", recommendation_style))
            if current:
                content.append(Paragraph(f"  Current: {current}", recommendation_style))
            if suggested:
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

# Alt style kept for parity

def generate_updated_resume1(resume_text, match_analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    styles["Heading1"].fontSize = 14
    styles["Heading1"].spaceAfter = 16
    styles["Heading1"].textColor = colors.HexColor("#2c3e50")

    styles["Heading2"].fontSize = 12
    styles["Heading2"].spaceAfter = 12
    styles["Heading2"].textColor = colors.HexColor("#34495e")

    styles["Normal"].fontSize = 10
    styles["Normal"].spaceAfter = 8
    styles["Normal"].leading = 14

    styles.add(
        ParagraphStyle(
            name="RecommendationStyle",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=8,
            leading=14,
            leftIndent=20,
            textColor=colors.HexColor("#2980b9"),
        )
    )

    content = []
    content.append(Paragraph("Updated Resume", styles["Heading1"]))
    content.append(Spacer(1, 12))

    resume_parts = [p for p in resume_text.split("\n") if p.strip()]
    for part in resume_parts:
        common_sections = ["EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "CERTIFICATIONS"]
        is_section = part.isupper() or any(section in part.upper() for section in common_sections)
        content.append(Paragraph(part, styles["Heading2"] if is_section else styles["Normal"]))
        content.append(Spacer(1, 6))

    if (match_analysis or {}).get("ats_optimization_suggestions"):
        content.append(Spacer(1, 12))
        content.append(Paragraph("ATS Optimization Recommendations", styles["Heading2"]))
        content.append(Spacer(1, 8))
        for suggestion in match_analysis["ats_optimization_suggestions"]:
            content.append(Paragraph(f"â€¢ Section: {suggestion.get('section','')}", styles["RecommendationStyle"]))
            if suggestion.get("current_content"):
                content.append(Paragraph(f"  Current: {suggestion['current_content']}", styles["RecommendationStyle"]))
            if suggestion.get("suggested_change"):
                content.append(Paragraph(f"  Suggestion: {suggestion['suggested_change']}", styles["RecommendationStyle"]))
            if suggestion.get("keywords_to_add"):
                content.append(Paragraph(
                    f"  Keywords to Add: {', '.join(suggestion['keywords_to_add'])}", styles["RecommendationStyle"]
                ))
            if suggestion.get("formatting_suggestion"):
                content.append(Paragraph(
                    f"  Formatting: {suggestion['formatting_suggestion']}", styles["RecommendationStyle"]
                ))
            content.append(Spacer(1, 6))

    doc.build(content)
    buffer.seek(0)
    return buffer

# =============================
# Domain logic using LLMClient
# =============================

class JobAnalyzer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze_job(self, job_description: str) -> dict:
        prompt = f"""
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
        Respond ONLY with a valid JSON object.
        Job Description:\n{job_description}
        """
        return self.llm.generate_json(prompt, temperature=0.1)

    def analyze_resume(self, resume_text: str) -> dict:
        prompt = f"""
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
        Respond ONLY with a valid JSON object.
        Resume:\n{resume_text}
        """
        return self.llm.generate_json(prompt, temperature=0.1)

    def analyze_match(self, job_analysis: dict, resume_analysis: dict) -> dict:
        structure = {
            "overall_match_percentage": "85%",
            "matching_skills": [{"skill_name": "Python", "is_match": True}],
            "missing_skills": [{"skill_name": "Docker", "is_match": False, "suggestion": "Consider obtaining Docker certification"}],
            "skills_gap_analysis": {"technical_skills": "", "soft_skills": ""},
            "experience_match_analysis": "",
            "education_match_analysis": "",
            "recommendations_for_improvement": [{"recommendation": "Add metrics", "section": "Experience", "guidance": "Quantify achievements with numbers"}],
            "ats_optimization_suggestions": [{
                "section": "Skills",
                "current_content": "Current format",
                "suggested_change": "Specific change needed",
                "keywords_to_add": ["keyword1", "keyword2"],
                "formatting_suggestion": "Specific format change",
                "reason": "Detailed reason"
            }],
            "key_strengths": "",
            "areas_of_improvement": ""
        }
        prompt = (
            "You are a professional resume analyzer. Compare the provided job requirements and resume to "
            "generate a detailed analysis in valid JSON. Respond ONLY with JSON matching this structure, "
            "filling it with specific, actionable content based on the inputs.\n\n"
            f"Job Requirements:\n{json.dumps(job_analysis, indent=2)}\n\n"
            f"Resume Details:\n{json.dumps(resume_analysis, indent=2)}\n\n"
            f"JSON schema example (use same keys, replace values):\n{json.dumps(structure, indent=2)}"
        )
        return self.llm.generate_json(prompt, temperature=0.2)

class CoverLetterGenerator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_cover_letter(self, job_analysis: dict, resume_analysis: dict, match_analysis: dict, tone: str = "professional") -> str:
        prompt = f"""
        Generate a compelling cover letter using this information:
        Job Details:\n{json.dumps(job_analysis, indent=2)}
        Candidate Details:\n{json.dumps(resume_analysis, indent=2)}
        Match Analysis:\n{json.dumps(match_analysis, indent=2)}
        Tone: {tone}
        Requirements:
        1. Make it personal and specific
        2. Highlight the strongest matches
        3. Address potential gaps professionally
        4. Keep it concise but impactful (200-300 words)
        5. Use the specified tone: {tone}
        6. Include specific examples from the resume
        7. Make it ATS-friendly
        8. End with a confident call to action
        """
        return self.llm.generate_text(prompt, temperature=0.7)

# =============================
# Streamlit app
# =============================

def resolve_api_key_from_inputs(user_input_key: str | None) -> str | None:
    # Priority: sidebar input > st.secrets > env var
    if user_input_key:
        return user_input_key.strip()
    
    # Safely check for secrets
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        # Secrets file doesn't exist or can't be accessed
        pass
    
    return os.getenv("GEMINI_API_KEY")


def main():
    st.set_page_config(page_title="JobFit-AI", layout="wide", initial_sidebar_state="collapsed")
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-title {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
    }
    .main-subtitle {
        font-size: 1.2rem;
        font-weight: 300;
        opacity: 0.9;
        margin: 0.5rem 0 0 0;
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        margin: 1rem 0;
        height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .feature-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 0.5rem;
    }
    .feature-desc {
        color: #666;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    .get-started-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem 0;
    }
    .upload-area {
        background: white;
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed #e0e0e0;
        text-align: center;
    }
    .settings-panel {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">🚀 JobFit-AI</h1>
        <p class="main-subtitle">AI-Powered Resume & Job Matching Assistant</p>
    </div>
    """, unsafe_allow_html=True)

    # Settings Panel
    st.markdown('<div class="settings-panel">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Configuration")
    
    col_set1, col_set2 = st.columns([2, 1])
    with col_set1:
        input_key = st.text_input("🔑 Google Gemini API Key", type="password", placeholder="Enter your API key here...")
    with col_set2:
        model_choice = st.selectbox("🤖 AI Model", SUPPORTED_MODELS, index=0)
    
    st.markdown('</div>', unsafe_allow_html=True)

    api_key = resolve_api_key_from_inputs(input_key)
    
    # Show welcome page when no API key is provided
    if not api_key:
        # Welcome Section
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <h2 style="color: #667eea; margin-bottom: 1rem;">🔑 Welcome to JobFit-AI!</h2>
            <p style="font-size: 1.1rem; color: #666; max-width: 600px; margin: 0 auto 2rem auto; line-height: 1.6;">
                To get started, please enter your Google Gemini API key above. 
                This allows our AI to analyze your resume and job descriptions to provide personalized insights.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # How to get API key section
        with st.expander("🔍 How to get your Google Gemini API Key", expanded=True):
            st.markdown("""
            **Follow these simple steps:**
            
            1. 🌐 Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
            2. 🔐 Sign in with your Google account
            3. ➕ Click **"Create API Key"**
            4. 📋 Copy the generated API key
            5. 📝 Paste it in the field above
            6. ✨ Start using JobFit-AI!
            
            **Note:** Your API key is only used during this session and is not stored anywhere.
            """)
        
        # Features preview
        st.markdown("---")
        st.markdown("## ✨ What You'll Get With JobFit-AI")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🎯</div>
                <div class="feature-title">Smart Job Matching</div>
                <div class="feature-desc">Get percentage match scores between your resume and job descriptions with detailed breakdowns</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Skills Gap Analysis</div>
                <div class="feature-desc">Identify exactly which skills you have, which you're missing, and how to improve</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">💌</div>
                <div class="feature-title">AI Cover Letters</div>
                <div class="feature-desc">Generate personalized, ATS-optimized cover letters in multiple tones</div>
            </div>
            """, unsafe_allow_html=True)
            
        col4, col5, col6 = st.columns(3)
        
        with col4:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-title">ATS Optimization</div>
                <div class="feature-desc">Get specific suggestions to make your resume pass Applicant Tracking Systems</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col5:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <div class="feature-title">Actionable Insights</div>
                <div class="feature-desc">Receive detailed recommendations for improving your job application success rate</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col6:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📄</div>
                <div class="feature-title">Enhanced Resume</div>
                <div class="feature-desc">Download an improved version of your resume with all optimization suggestions applied</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Call to action
        st.markdown("""
        <div style="text-align: center; background: #f0f2f6; padding: 2rem; border-radius: 10px; margin: 2rem 0;">
            <h3 style="color: #667eea; margin-bottom: 1rem;">🚀 Ready to Boost Your Job Search?</h3>
            <p style="color: #666; font-size: 1.1rem;">
                Enter your Google Gemini API key above to unlock the power of AI-driven job matching!
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.stop()

    try:
        llm = LLMClient(api_key=api_key, model_name=model_choice)
    except Exception as e:
        st.error(f"❌ Failed to initialize AI model: {e}")
        st.stop()

    job_analyzer = JobAnalyzer(llm)
    cover_letter_gen = CoverLetterGenerator(llm)

    # Get Started Section
    st.markdown('<div class="get-started-section">', unsafe_allow_html=True)
    st.markdown("## 🚀 Get Started")
    st.markdown("Upload your resume and paste a job description to begin the analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Job Description")
        job_desc = st.text_area(
            "Paste the job description here", 
            height=300, 
            placeholder="Copy and paste the complete job description from the company's website..."
        )
        
    with col2:
        st.markdown("### 📄 Your Resume")
        resume_file = st.file_uploader(
            "Upload your resume", 
            type=["pdf", "docx"],
            help="Supported formats: PDF and DOCX files"
        )
        
    st.markdown('</div>', unsafe_allow_html=True)

    if not job_desc and not resume_file:
        st.info("👆 Please provide both a job description and upload your resume to start the analysis.")
        return
    elif not job_desc:
        st.warning("📋 Please paste the job description to continue.")
        return
    elif not resume_file:
        st.warning("📄 Please upload your resume to continue.")
        return

    # Analysis Section
    with st.spinner("🔍 Analyzing your application... This may take a moment."):
        resume_text = load_resume(resume_file)
        if not resume_text:
            st.error("❌ Could not read your resume. Please try uploading a different file.")
            return

        job_analysis = job_analyzer.analyze_job(job_desc)
        resume_analysis = job_analyzer.analyze_resume(resume_text)
        match_analysis = job_analyzer.analyze_match(job_analysis, resume_analysis)

    if not (job_analysis and resume_analysis and match_analysis):
        st.error("❌ Insufficient data returned from the AI model. Please try again or adjust the model settings.")
        return

    st.success("✅ Analysis completed successfully!")
    st.markdown("---")
    st.header("📊 Analysis Results")

    # Metrics Section
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("🎯 Overall Match", f"{match_analysis.get('overall_match_percentage', '0%')}")
    with col_m2:
        st.metric("✅ Matching Skills", f"{len(match_analysis.get('matching_skills', []))}")
    with col_m3:
        st.metric("📈 Skills to Develop", f"{len(match_analysis.get('missing_skills', []))}")
    with col_m4:
        match_percent = match_analysis.get('overall_match_percentage', '0%')
        try:
            match_num = int(match_percent.replace('%', ''))
            if match_num >= 80:
                st.metric("🏆 Match Quality", "Excellent", delta="High compatibility")
            elif match_num >= 60:
                st.metric("👍 Match Quality", "Good", delta="Strong potential")
            else:
                st.metric("💪 Match Quality", "Needs Work", delta="Room for improvement")
        except:
            st.metric("🎯 Match Quality", "Calculating...")

    # Detailed Analysis Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Skills Analysis",
        "🗂️ Experience Match",
        "💡 Recommendations",
        "💌 Cover Letter",
        "📄 Updated Resume",
    ])

    with tab1:
        st.subheader("✅ Matching Skills")
        if match_analysis.get("matching_skills"):
            for skill in match_analysis.get("matching_skills", []):
                st.success(f"✅ {skill.get('skill_name', '')}")
        else:
            st.info("No matching skills identified.")
            
        st.subheader("⚠️ Missing Skills")
        if match_analysis.get("missing_skills"):
            for skill in match_analysis.get("missing_skills", []):
                label = skill.get("skill_name", "")
                st.warning(f"⚠️ {label}")
                if skill.get("suggestion"):
                    st.info(f"💡 Suggestion: {skill['suggestion']}")
        else:
            st.success("Great! No critical skills are missing.")

        # Skills Chart
        matching_skills_count = len(match_analysis.get("matching_skills", []))
        missing_skills_count = len(match_analysis.get("missing_skills", []))
        if matching_skills_count > 0 or missing_skills_count > 0:
            skills_data = pd.DataFrame({
                "Status": ["Matching", "Missing"],
                "Count": [matching_skills_count, missing_skills_count],
            })
            fig = px.bar(
                skills_data,
                x="Status",
                y="Count",
                color="Status",
                color_discrete_sequence=["#5cb85c", "#d9534f"],
                title="Skills Analysis Overview",
            )
            fig.update_layout(
                xaxis_title="Status", 
                yaxis_title="Count",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.write("### 🗂️ Experience Match Analysis")
        exp_analysis = match_analysis.get("experience_match_analysis", "")
        if exp_analysis:
            st.write(exp_analysis)
        else:
            st.info("Experience analysis not available.")
            
        st.write("### 🎓 Education Match Analysis")
        edu_analysis = match_analysis.get("education_match_analysis", "")
        if edu_analysis:
            st.write(edu_analysis)
        else:
            st.info("Education analysis not available.")

    with tab3:
        st.write("### 🔑 Key Recommendations")
        recommendations = match_analysis.get("recommendations_for_improvement", [])
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                with st.container():
                    st.info(f"**{i}. {rec.get('recommendation','')}**")
                    if rec.get("section"):
                        st.write(f"📍 **Section:** {rec['section']}")
                    if rec.get("guidance"):
                        st.write(f"🎯 **Guidance:** {rec['guidance']}")
                    st.markdown("---")
        else:
            st.success("🎉 No specific recommendations needed - your profile looks great!")

        st.write("### 🤖 ATS Optimization Suggestions")
        ats_suggestions = match_analysis.get("ats_optimization_suggestions", [])
        if ats_suggestions:
            for i, suggestion in enumerate(ats_suggestions, 1):
                with st.expander(f"📝 Suggestion {i}: {suggestion.get('section','')}"):
                    if suggestion.get("current_content"):
                        st.write(f"**Current Content:** {suggestion['current_content']}")
                    if suggestion.get("suggested_change"):
                        st.write(f"**Suggested Change:** {suggestion['suggested_change']}")
                    if suggestion.get("keywords_to_add"):
                        st.write(f"**Keywords to Add:** {', '.join(suggestion['keywords_to_add'])}")
                    if suggestion.get("formatting_suggestion"):
                        st.write(f"**Formatting Changes:** {suggestion['formatting_suggestion']}")
                    if suggestion.get("reason"):
                        st.info(f"**Why this matters:** {suggestion['reason']}")
        else:
            st.success("🎉 Your resume is already well-optimized for ATS systems!")

    with tab4:
        st.write("### 🖊️ AI-Powered Cover Letter Generator")
        
        col_tone1, col_tone2 = st.columns([2, 1])
        with col_tone1:
            tone_map = {
                "Professional 👔": "professional",
                "Enthusiastic 😃": "enthusiastic",
                "Confident 😎": "confident",
                "Friendly 👋": "friendly",
            }
            chosen = st.selectbox("🎭 Select tone for your cover letter", list(tone_map.keys()))
        with col_tone2:
            st.markdown("<br>", unsafe_allow_html=True)
            generate_btn = st.button("✏️ Generate Cover Letter", type="primary")
            
        if generate_btn:
            with st.spinner("✏️ Crafting your personalized cover letter..."):
                cover_letter = cover_letter_gen.generate_cover_letter(
                    job_analysis, resume_analysis, match_analysis, tone=tone_map[chosen]
                )
                
            st.markdown("### 💌 Your Custom Cover Letter")
            st.text_area("", cover_letter, height=400, key="cover_letter_display")
            
            col_dl1, col_dl2 = st.columns([1, 3])
            with col_dl1:
                st.download_button(
                    "📥 Download Cover Letter", 
                    cover_letter, 
                    "cover_letter.txt", 
                    "text/plain"
                )
            with col_dl2:
                st.success("✨ Cover letter generated successfully! You can copy the text above or download it.")

    with tab5:
        st.write("### 📄 Enhanced Resume")
        st.info("💡 Download an improved version of your resume with ATS optimization suggestions included.")
        
        col_res1, col_res2 = st.columns([1, 3])
        with col_res1:
            updated_resume = generate_updated_resume(resume_text, match_analysis)
            st.download_button(
                "📥 Download Enhanced Resume",
                updated_resume,
                "enhanced_resume.pdf",
                mime="application/pdf",
                type="primary"
            )
        with col_res2:
            st.markdown("""
            **Your enhanced resume includes:**
            - Original resume content with improved formatting
            - ATS optimization recommendations
            - Suggested keywords and phrases
            - Professional styling and layout
            """)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <p>🚀 <strong>JobFit-AI</strong> - Powered by Google Gemini AI</p>
        <p>Made with ❤️ to help you land your dream job</p>
        <p>🤝Made by Ashutosh Kumar Yadav</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
