"""
Production CV Matching Server - LGIR
Tách riêng 2 routes:
1. POST /parse - Parse PDF CV thành JSON
2. POST /score - Chấm điểm CV matching với job descriptions

Deploy-ready cho AWS EC2
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import openai
import json
import pdfplumber
import io
import uvicorn
import logging
from datetime import datetime
import os

# ============================================================================
# Configuration
# ============================================================================

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="LGIR CV Matching API - Production",
    version="3.0.0",
    description="Parse PDF CVs and match with job descriptions using LGIR"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update này khi deploy production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in .env file")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# LGIR Parameters
KAPPA_1 = 5  # Many-shot threshold
KAPPA_2 = 2  # Few-shot threshold
TEMPERATURE = 0.0  # Deterministic scoring


# ============================================================================
# Data Models
# ============================================================================

class Education(BaseModel):
    degree: str
    institution: str
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None

class Experience(BaseModel):
    title: str
    company: str
    duration: str
    responsibilities: List[str]
    achievements: Optional[List[str]] = []

class CV(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str]
    education: List[Education]
    experience: List[Experience]
    certifications: Optional[List[str]] = []
    languages: Optional[List[str]] = []

class JobDescription(BaseModel):
    title: str
    company: str
    requirements: List[str]
    responsibilities: List[str]
    preferred_qualifications: Optional[List[str]] = []
    required_skills: List[str]

class InteractionHistory(BaseModel):
    job_descriptions: List[JobDescription]
    interaction_count: int

class ParseRequest(BaseModel):
    """Request for text parsing (if already extracted from PDF)"""
    cv_text: str

class ParseResponse(BaseModel):
    success: bool
    cv_data: Optional[CV] = None
    error: Optional[str] = None
    message: str

class ScoreRequest(BaseModel):
    cv: CV
    target_jobs: List[JobDescription]
    interaction_history: Optional[InteractionHistory] = None

class JobMatchScore(BaseModel):
    job_title: str
    company: str
    overall_score: float
    skills_match_score: float
    experience_match_score: float
    education_match_score: float
    strengths: List[str]
    gaps: List[str]
    suggestions: List[str]
    resume_quality: str

class ScoreResponse(BaseModel):
    success: bool
    cv_name: str
    job_matches: List[JobMatchScore]
    overall_suggestions: List[str]
    cv_strengths: List[str]
    cv_weaknesses: List[str]
    resume_completion_method: str
    is_few_shot_user: bool
    interaction_count: int
    deterministic: bool = True
    error: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def call_llm(messages: List[Dict], max_tokens: int = 1000) -> str:
    """Call OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=max_tokens
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean markdown
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        return result_text.strip()
        
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        raise


# ============================================================================
# ROUTE 1: PARSE PDF CV
# ============================================================================

@app.post("/parse/pdf", response_model=ParseResponse)
async def parse_pdf_cv(file: UploadFile = File(...)):
    """
    Parse PDF CV file thành JSON format
    
    Upload PDF file → Returns structured CV data
    """
    logger.info(f"📄 Parsing PDF: {file.filename}")
    
    try:
        # Step 1: Extract text from PDF
        contents = await file.read()
        pdf_file = io.BytesIO(contents)
        
        cv_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            logger.info(f"   Pages: {len(pdf.pages)}")
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    cv_text += text + "\n\n"
        
        if not cv_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Cannot extract text from PDF. PDF may be image-based or corrupted."
            )
        
        logger.info(f"✅ Extracted {len(cv_text)} characters")
        
        # Step 2: Parse with AI
        cv_data = await parse_cv_text_internal(cv_text)
        
        logger.info(f"✅ Parsed CV: {cv_data.name}")
        
        return ParseResponse(
            success=True,
            cv_data=cv_data,
            message=f"Successfully parsed CV: {cv_data.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Parse error: {e}")
        return ParseResponse(
            success=False,
            error=str(e),
            message="Failed to parse PDF"
        )


@app.post("/parse/text", response_model=ParseResponse)
async def parse_text_cv(request: ParseRequest):
    """
    Parse CV text (already extracted) thành JSON format
    
    Useful if you already have CV text extracted
    """
    logger.info("📝 Parsing CV text")
    
    try:
        cv_data = await parse_cv_text_internal(request.cv_text)
        
        logger.info(f"✅ Parsed CV: {cv_data.name}")
        
        return ParseResponse(
            success=True,
            cv_data=cv_data,
            message=f"Successfully parsed CV: {cv_data.name}"
        )
        
    except Exception as e:
        logger.error(f"❌ Parse error: {e}")
        return ParseResponse(
            success=False,
            error=str(e),
            message="Failed to parse CV text"
        )


async def parse_cv_text_internal(cv_text: str) -> CV:
    """Internal function to parse CV text using AI"""
    
    prompt = f"""You are an expert CV parser. Extract information from this CV and return it in JSON format.

CV TEXT:
{cv_text}

Please extract and return in this EXACT JSON format:
{{
    "name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "summary": "Professional summary",
    "skills": ["skill1", "skill2", ...],
    "education": [
        {{
            "degree": "Degree name",
            "institution": "School name",
            "graduation_year": 2020,
            "gpa": 3.5
        }}
    ],
    "experience": [
        {{
            "title": "Job title",
            "company": "Company name",
            "duration": "Duration string",
            "responsibilities": ["Task 1", "Task 2", ...],
            "achievements": ["Achievement 1", ...]
        }}
    ],
    "certifications": ["Cert 1", ...],
    "languages": ["Language 1", ...]
}}

Rules:
1. Extract ALL skills mentioned
2. Keep original language (Vietnamese or English)
3. If field not found, use empty list [] or null
4. Return ONLY valid JSON

JSON:"""

    messages = [
        {"role": "system", "content": "You are an expert CV parser. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    result_text = call_llm(messages, max_tokens=2000)
    cv_data_dict = json.loads(result_text)
    
    # Convert to CV model
    education_list = [
        Education(**edu) for edu in cv_data_dict.get('education', [])
    ]
    
    experience_list = [
        Experience(**exp) for exp in cv_data_dict.get('experience', [])
    ]
    
    cv = CV(
        name=cv_data_dict.get('name', 'Unknown'),
        email=cv_data_dict.get('email', ''),
        phone=cv_data_dict.get('phone'),
        summary=cv_data_dict.get('summary'),
        skills=cv_data_dict.get('skills', []),
        education=education_list,
        experience=experience_list,
        certifications=cv_data_dict.get('certifications', []),
        languages=cv_data_dict.get('languages', [])
    )
    
    return cv


# ============================================================================
# ROUTE 2: SCORE CV MATCHING
# ============================================================================

@app.post("/score", response_model=ScoreResponse)
async def score_cv_matching(request: ScoreRequest):
    """
    Chấm điểm CV matching với job descriptions sử dụng LGIR
    
    Input: CV + Target Jobs + Interaction History (optional)
    Output: Scores, Strengths, Gaps, Suggestions
    """
    logger.info(f"🎯 Scoring CV: {request.cv.name}")
    logger.info(f"   Target jobs: {len(request.target_jobs)}")
    
    try:
        # Step 1: Determine user type
        interaction_count = 0
        if request.interaction_history:
            interaction_count = request.interaction_history.interaction_count
        
        is_few_shot = interaction_count <= KAPPA_2
        is_many_shot = interaction_count >= KAPPA_1
        
        logger.info(f"   User type: {'Few-shot' if is_few_shot else 'Many-shot' if is_many_shot else 'Medium-shot'}")
        
        # Step 2: Resume Completion
        if request.interaction_history and interaction_count > 0:
            completed_resume = interactive_resume_completion(
                request.cv, request.interaction_history
            )
            completion_method = "interactive"
        else:
            completed_resume = simple_resume_completion(request.cv)
            completion_method = "simple"
        
        logger.info(f"   Method: {completion_method}")
        
        # Step 3: Quality Detection
        is_high_quality, quality_label, quality_score = detect_resume_quality(
            request.cv, interaction_count, completed_resume
        )
        
        # Step 4: GAN Refinement
        refined_resume, was_refined = refine_resume_with_gan(
            completed_resume, not is_high_quality
        )
        
        final_quality_label = "refined" if was_refined else quality_label
        
        quality_info = {
            "quality_label": final_quality_label,
            "method": completion_method,
            "was_refined": was_refined,
            "quality_score": quality_score
        }
        
        logger.info(f"   Quality: {final_quality_label}")
        
        # Step 5: Match against jobs
        job_matches = []
        for jd in request.target_jobs:
            analysis = analyze_cv_job_match(
                request.cv, jd, refined_resume, quality_info
            )
            
            job_match = JobMatchScore(
                job_title=jd.title,
                company=jd.company,
                overall_score=analysis.get("overall_score", 0),
                skills_match_score=analysis.get("skills_match_score", 0),
                experience_match_score=analysis.get("experience_match_score", 0),
                education_match_score=analysis.get("education_match_score", 0),
                strengths=analysis.get("strengths", []),
                gaps=analysis.get("gaps", []),
                suggestions=analysis.get("suggestions", []),
                resume_quality=final_quality_label
            )
            job_matches.append(job_match)
            
            logger.info(f"   ✓ {jd.title}: {job_match.overall_score:.1f}/100")
        
        # Step 6: Overall analysis
        overall_analysis = generate_overall_analysis(
            request.cv, completion_method, final_quality_label,
            is_few_shot, interaction_count, quality_score, was_refined
        )
        
        response = ScoreResponse(
            success=True,
            cv_name=request.cv.name,
            job_matches=sorted(job_matches, key=lambda x: x.overall_score, reverse=True),
            overall_suggestions=overall_analysis["suggestions"],
            cv_strengths=overall_analysis["strengths"],
            cv_weaknesses=overall_analysis["weaknesses"],
            resume_completion_method=completion_method,
            is_few_shot_user=is_few_shot,
            interaction_count=interaction_count,
            deterministic=True
        )
        
        logger.info(f"✅ Scoring complete for {request.cv.name}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Scoring error: {e}")
        return ScoreResponse(
            success=False,
            cv_name=request.cv.name,
            job_matches=[],
            overall_suggestions=[],
            cv_strengths=[],
            cv_weaknesses=[],
            resume_completion_method="",
            is_few_shot_user=False,
            interaction_count=0,
            error=str(e)
        )


# ============================================================================
# LGIR Helper Functions
# ============================================================================

def simple_resume_completion(cv: CV) -> str:
    """Simple Resume Completion"""
    prompt = f"""Improve this resume to highlight skills and experience.

Resume:
Name: {cv.name}
Skills: {', '.join(cv.skills)}
Experience: {len(cv.experience)} positions
Education: {len(cv.education)} entries

Generate improved resume in JSON format with: skills, experience_summary, key_strengths."""
    
    messages = [
        {"role": "system", "content": "You are an expert resume writer. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    result = call_llm(messages, max_tokens=800)
    return result


def interactive_resume_completion(cv: CV, history: InteractionHistory) -> str:
    """Interactive Resume Completion using interaction history"""
    interest_text = "\n".join([
        f"{i+1}. {job.title} at {job.company}: {', '.join(job.required_skills[:3])}"
        for i, job in enumerate(history.job_descriptions[:5])
    ])
    
    prompt = f"""Improve resume based on user's interaction history to infer implicit skills.

Resume:
Name: {cv.name}
Skills: {', '.join(cv.skills)}

Jobs user interacted with:
{interest_text}

Generate improved resume in JSON with: skills (enhanced), experience_summary, key_strengths, inferred_interests."""
    
    messages = [
        {"role": "system", "content": "Expert resume analyst. Infer implicit skills from interactions. Return only JSON."},
        {"role": "user", "content": prompt}
    ]
    
    result = call_llm(messages, max_tokens=1000)
    return result


def detect_resume_quality(cv: CV, interaction_count: int, completed_resume: str) -> tuple:
    """Detect resume quality based on interaction count"""
    if interaction_count >= KAPPA_1:
        return True, "high-quality", 0.9
    elif interaction_count <= KAPPA_2:
        return False, "low-quality", 0.3
    else:
        quality_score = min(0.9, 0.3 + (interaction_count - KAPPA_2) * 0.2)
        is_high_quality = quality_score >= 0.5
        label = "high-quality" if is_high_quality else "low-quality"
        return is_high_quality, label, quality_score


def refine_resume_with_gan(completed_resume: str, is_low_quality: bool) -> tuple:
    """GAN-based refinement for low-quality resumes"""
    if not is_low_quality:
        return completed_resume, False
    
    prompt = f"""Refine this resume from limited interaction history to be more comprehensive and professional.

Resume:
{completed_resume}

Generate refined version in same JSON format with more specific technical details."""
    
    messages = [
        {"role": "system", "content": "Expert at refining resumes. Generate high-quality, detailed resumes."},
        {"role": "user", "content": prompt}
    ]
    
    refined = call_llm(messages, max_tokens=1000)
    return refined, True


def analyze_cv_job_match(cv: CV, jd: JobDescription, completed_resume: str, quality_info: Dict) -> Dict:
    """Analyze CV vs Job match"""
    
    cv_text = f"""CV: {cv.name}
Skills: {', '.join(cv.skills)}
Experience: {len(cv.experience)} positions
Education: {', '.join([edu.degree for edu in cv.education])}

Enhanced: {completed_resume}"""

    jd_text = f"""Job: {jd.title} at {jd.company}
Required Skills: {', '.join(jd.required_skills)}
Requirements: {', '.join(jd.requirements[:3])}"""

    prompt = f"""Analyze candidate vs job. Resume quality: {quality_info['quality_label']}, Method: {quality_info['method']}.

{cv_text}

{jd_text}

Return JSON:
{{
    "overall_score": <0-100>,
    "skills_match_score": <0-100>,
    "experience_match_score": <0-100>,
    "education_match_score": <0-100>,
    "strengths": [<3-5 items>],
    "gaps": [<3-5 items>],
    "suggestions": [<5-7 items>]
}}"""

    messages = [
        {"role": "system", "content": "Expert HR recruiter. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    result = call_llm(messages, max_tokens=1500)
    return json.loads(result)


def generate_overall_analysis(cv, method, quality, is_few_shot, count, score, refined):
    """Generate overall CV analysis"""
    return {
        "strengths": [
            f"{'Interactive' if method == 'interactive' else 'Basic'} resume completion applied",
            f"Resume quality: {quality}",
            f"User type: {'Few-shot' if is_few_shot else 'Many-shot'}"
        ],
        "weaknesses": [
            f"Limited interaction history ({count} interactions)" if is_few_shot else "Good interaction history",
            "GAN refinement applied" if refined else "No refinement needed"
        ],
        "suggestions": [
            "Continue applying to build interaction history" if is_few_shot else "Good engagement",
            "Resume enhanced using LGIR methodology",
            f"Quality score: {score:.2f}/1.0"
        ]
    }


# ============================================================================
# Health Check & Info Routes
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": "LGIR CV Matching API - Production",
        "version": "3.0.0",
        "status": "active",
        "routes": {
            "parse_pdf": "POST /parse/pdf - Upload PDF CV to parse",
            "parse_text": "POST /parse/text - Parse CV text",
            "score": "POST /score - Score CV matching with jobs",
            "health": "GET /health - Health check",
            "docs": "GET /docs - API documentation"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(OPENAI_API_KEY),
        "temperature": TEMPERATURE,
        "deterministic": True
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8000))
    
    print("="*80)
    print("🚀 LGIR CV Matching API - Production Server")
    print("="*80)
    print(f"\n📍 Running on: http://0.0.0.0:{port}")
    print(f"📚 API Docs: http://0.0.0.0:{port}/docs")
    print("\n🔧 Routes:")
    print("   POST /parse/pdf  - Parse PDF CV")
    print("   POST /parse/text - Parse text CV")
    print("   POST /score      - Score CV matching")
    print("   GET  /health     - Health check")
    print("\n" + "="*80 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

