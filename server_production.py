"""
Production CV Matching Server - LGIR
Tách riêng 2 routes:
1. POST /parse - Parse PDF CV thành JSON
2. POST /score - Chấm điểm CV matching với job descriptions

Deploy-ready cho AWS EC2
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional
import openai
import json
import pdfplumber
import io
import uvicorn
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Import skill processing modules
try:
    from skill_processor import (
        calculate_skill_gap,
        format_skill_gap_for_prompt,
        format_skill_gap_json,
        get_learning_recommendations,
        extract_skills_from_list
    )
    from skill_ontology import get_skill, normalize_skill_name, get_all_skills
    from rag_knowledge import (
        get_rag_context_for_evaluation,
        retrieve_skill_knowledge,
        retrieve_resume_tips,
        CAREER_PATHS
    )
    SKILL_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Skill modules not available: {e}")
    SKILL_MODULES_AVAILABLE = False

# Load environment variables
load_dotenv()

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
    description: Optional[str] = None
    gpa: Optional[float] = None

class Experience(BaseModel):
    title: str
    company: str
    duration: str
    description: Optional[str] = None
    responsibilities: List[str]
    achievements: Optional[List[str]] = []

class Project(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: Optional[List[str]] = []
    url: Optional[str] = None
    duration: Optional[str] = None
    role: Optional[str] = None
    achievements: Optional[List[str]] = []

class CV(BaseModel):
    model_config = ConfigDict(ser_json_timedelta='iso8601')
    
    name: str
    email: str
    phone: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str]
    education: List[Education]
    experience: List[Experience]
    projects: List[Project] = []
    certifications: List[str] = []
    languages: List[str] = []
    achievements: List[str] = []

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
# NEW: CV Evaluation Models (Single Score Output)
# ============================================================================

class EvaluateRequest(BaseModel):
    """Request để đánh giá CV - trả về MỘT điểm duy nhất"""
    cv: CV
    interaction_history: Optional[InteractionHistory] = None


class EvaluateWithJDRequest(BaseModel):
    """Request để đánh giá CV với target JD và các similar JDs tham khảo"""
    cv: CV
    target_jd: JobDescription                    # JD chính, chú trọng nhất
    similar_jds: Optional[List[JobDescription]] = []  # JDs tương tự để tham khảo thêm

class ScoreBreakdown(BaseModel):
    """Chi tiết điểm từng tiêu chí"""
    skills_score: float              # Điểm kỹ năng (0-100)
    experience_score: float          # Điểm kinh nghiệm (0-100)
    education_score: float           # Điểm học vấn (0-100)
    completeness_score: float        # Độ đầy đủ CV (0-100)
    job_alignment_score: float       # Độ phù hợp với jobs đã apply (0-100)
    presentation_score: float        # Điểm trình bày/format (0-100)


class CVEdit(BaseModel):
    """Đề xuất sửa cụ thể một field trong CV JSON"""
    field_path: str                  # Path đến field cần sửa, e.g., "skills", "experience[0].achievements"
    action: str                      # "add", "update", "remove", "rewrite"
    current_value: Optional[str] = None    # Giá trị hiện tại (nếu có)
    suggested_value: str             # Giá trị đề xuất
    reason: str                      # Lý do cần sửa
    priority: str                    # "high", "medium", "low"
    impact_score: Optional[float] = None   # Điểm tăng dự kiến nếu sửa


class SkillGapInfo(BaseModel):
    """Thông tin skill gap analysis"""
    match_percentage: float          # % skills match
    gap_severity: str               # "low", "medium", "high", "critical"
    matching_skills: List[str]      # Skills có trong cả CV và JD
    missing_skills: List[str]       # Skills JD yêu cầu mà CV thiếu
    extra_skills: List[str]         # Skills CV có mà JD không yêu cầu
    high_priority_missing: List[str]  # Missing skills có demand cao
    quick_wins: List[str]           # Skills dễ học dựa trên skills hiện có


class EvaluateResponse(BaseModel):
    """Response với MỘT điểm tổng hợp duy nhất"""
    success: bool
    cv_name: str
    
    # === MỘT ĐIỂM DUY NHẤT ===
    overall_score: float             # Điểm tổng (0-100)
    grade: str                       # Xếp hạng: A, B, C, D, F
    
    # Chi tiết điểm
    score_breakdown: ScoreBreakdown
    
    # Phân tích
    strengths: List[str]             # Điểm mạnh
    weaknesses: List[str]            # Điểm yếu
    recommendations: List[str]       # Gợi ý cải thiện
    
    # === ĐỀ XUẤT SỬA CV CỤ THỂ ===
    cv_edits: List[CVEdit]           # Danh sách các đề xuất sửa cụ thể trong JSON
    
    # === SKILL GAP ANALYSIS (NEW) ===
    skill_gap: Optional[SkillGapInfo] = None  # Phân tích skill gap chi tiết
    
    # Metadata
    jobs_analyzed: int               # Số jobs đã phân tích
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
            "description": "Description of study/major",
            "gpa": 3.5
        }}
    ],
    "experience": [
        {{
            "title": "Job title",
            "company": "Company name",
            "duration": "Duration string",
            "description": "Brief description of the role",
            "responsibilities": ["Task 1", "Task 2", ...],
            "achievements": ["Achievement 1", ...]
        }}
    ],
    "projects": [
        {{
            "name": "Project name",
            "description": "What the project does",
            "technologies": ["Tech 1", "Tech 2", ...],
            "url": "Project URL if any",
            "duration": "Duration string",
            "role": "Your role in the project",
            "achievements": ["Achievement 1", ...]
        }}
    ],
    "certifications": ["Cert 1", ...],
    "languages": ["Language 1", ...],
    "achievements": ["Overall achievement 1", ...]
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
    
    project_list = [
        Project(**proj) for proj in cv_data_dict.get('projects', [])
    ]
    
    cv = CV(
        name=cv_data_dict.get('name', 'Unknown'),
        email=cv_data_dict.get('email', ''),
        phone=cv_data_dict.get('phone'),
        summary=cv_data_dict.get('summary'),
        skills=cv_data_dict.get('skills', []),
        education=education_list,
        experience=experience_list,
        projects=project_list,
        certifications=cv_data_dict.get('certifications', []),
        languages=cv_data_dict.get('languages', []),
        achievements=cv_data_dict.get('achievements', [])
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
# ROUTE 3: EVALUATE CV (Single Score)
# ============================================================================

@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_cv(request: EvaluateRequest):
    """
    Đánh giá CV và trả về MỘT ĐIỂM TỔNG HỢP DUY NHẤT
    
    Tiêu chí đánh giá:
    - Skills: Số lượng và chất lượng kỹ năng
    - Experience: Kinh nghiệm làm việc
    - Education: Trình độ học vấn
    - Completeness: Độ đầy đủ thông tin CV
    - Job Alignment: Độ phù hợp với jobs đã apply (nếu có)
    - Presentation: Chất lượng trình bày
    
    Output: MỘT điểm overall_score (0-100) và grade (A-F)
    """
    logger.info(f"📊 Evaluating CV: {request.cv.name}")
    
    try:
        cv = request.cv
        interaction_count = 0
        jobs_list = []
        
        if request.interaction_history:
            interaction_count = request.interaction_history.interaction_count
            jobs_list = request.interaction_history.job_descriptions
        
        logger.info(f"   Jobs in history: {len(jobs_list)}")
        
        # Gọi LLM để đánh giá tổng hợp
        evaluation = evaluate_cv_comprehensive(cv, jobs_list)
        
        # Tính điểm tổng hợp (weighted average)
        breakdown = evaluation["breakdown"]
        
        # Trọng số cho từng tiêu chí
        weights = {
            "skills": 0.25,
            "experience": 0.25,
            "education": 0.15,
            "completeness": 0.15,
            "job_alignment": 0.10,
            "presentation": 0.10
        }
        
        overall_score = (
            breakdown["skills_score"] * weights["skills"] +
            breakdown["experience_score"] * weights["experience"] +
            breakdown["education_score"] * weights["education"] +
            breakdown["completeness_score"] * weights["completeness"] +
            breakdown["job_alignment_score"] * weights["job_alignment"] +
            breakdown["presentation_score"] * weights["presentation"]
        )
        
        # Xác định grade
        grade = calculate_grade(overall_score)
        
        logger.info(f"✅ Evaluation complete: {overall_score:.1f}/100 (Grade: {grade})")
        
        # Parse cv_edits từ evaluation
        cv_edits_raw = evaluation.get("cv_edits", [])
        cv_edits = []
        for edit in cv_edits_raw:
            # Xử lý suggested_value: convert sang string nếu là list/dict
            suggested_val = edit.get("suggested_value", "")
            if isinstance(suggested_val, (list, dict)):
                suggested_val = json.dumps(suggested_val, ensure_ascii=False)
            elif suggested_val is None:
                suggested_val = ""
            else:
                suggested_val = str(suggested_val)
            
            # Xử lý current_value tương tự
            current_val = edit.get("current_value")
            if isinstance(current_val, (list, dict)):
                current_val = json.dumps(current_val, ensure_ascii=False)
            elif current_val is not None:
                current_val = str(current_val)
            
            try:
                cv_edits.append(
                    CVEdit(
                        field_path=edit.get("field_path", ""),
                        action=edit.get("action", "add"),
                        current_value=current_val,
                        suggested_value=suggested_val,
                        reason=edit.get("reason", ""),
                        priority=edit.get("priority", "medium"),
                        impact_score=edit.get("impact_score")
                    )
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse cv_edit: {e}. Skipping this edit.")
                continue
        
        logger.info(f"   CV Edits suggested: {len(cv_edits)}")
        
        return EvaluateResponse(
            success=True,
            cv_name=cv.name,
            overall_score=round(overall_score, 1),
            grade=grade,
            score_breakdown=ScoreBreakdown(
                skills_score=breakdown["skills_score"],
                experience_score=breakdown["experience_score"],
                education_score=breakdown["education_score"],
                completeness_score=breakdown["completeness_score"],
                job_alignment_score=breakdown["job_alignment_score"],
                presentation_score=breakdown["presentation_score"]
            ),
            strengths=evaluation["strengths"],
            weaknesses=evaluation["weaknesses"],
            recommendations=evaluation["recommendations"],
            cv_edits=cv_edits,
            jobs_analyzed=len(jobs_list),
            deterministic=True
        )
        
    except Exception as e:
        logger.error(f"❌ Evaluation error: {e}")
        return EvaluateResponse(
            success=False,
            cv_name=request.cv.name,
            overall_score=0,
            grade="F",
            score_breakdown=ScoreBreakdown(
                skills_score=0, experience_score=0, education_score=0,
                completeness_score=0, job_alignment_score=0, presentation_score=0
            ),
            strengths=[],
            weaknesses=[],
            recommendations=[],
            cv_edits=[],
            jobs_analyzed=0,
            error=str(e)
        )


def evaluate_cv_comprehensive(cv: CV, jobs_list: List[JobDescription]) -> Dict:
    """Đánh giá CV tổng hợp với LLM + đề xuất sửa cụ thể"""
    
    # Chuẩn bị thông tin CV chi tiết cho việc đề xuất sửa
    cv_json_structure = f"""
CV JSON Structure:
{{
  "name": "{cv.name}",
  "email": "{cv.email}",
  "phone": "{cv.phone or 'null'}",
  "summary": "{(cv.summary or 'null')[:100]}...",
  "skills": {json.dumps(cv.skills[:10] if cv.skills else [], ensure_ascii=False)}{"..." if len(cv.skills) > 10 else ""},
  "education": [
{chr(10).join([f'    {{"degree": "{edu.degree}", "institution": "{edu.institution}", "gpa": {edu.gpa or "null"}}}' for edu in cv.education[:3]])}
  ],
  "experience": [
{chr(10).join([f'    {{"title": "{exp.title}", "company": "{exp.company}", "duration": "{exp.duration}", "responsibilities": {len(exp.responsibilities)} items, "achievements": {len(exp.achievements or [])} items}}' for exp in cv.experience[:3]])}
  ],
  "certifications": {json.dumps(cv.certifications[:5] if cv.certifications else [], ensure_ascii=False)},
  "languages": {json.dumps(cv.languages[:5] if cv.languages else [], ensure_ascii=False)}
}}
"""

    cv_info = f"""
CV Information:
- Name: {cv.name}
- Email: {cv.email}
- Phone: {cv.phone or 'Not provided'}
- Summary: {cv.summary or 'Not provided'}
- Skills: {', '.join(cv.skills) if cv.skills else 'None listed'}
- Number of skills: {len(cv.skills)}
- Education entries: {len(cv.education)}
- Experience entries: {len(cv.experience)}
- Certifications: {len(cv.certifications or [])}
- Languages: {len(cv.languages or [])}

Education Details:
{chr(10).join([f"  - {edu.degree} at {edu.institution}" + (f" (GPA: {edu.gpa})" if edu.gpa else "") for edu in cv.education]) if cv.education else "  None"}

Experience Details:
{chr(10).join([f"  - {exp.title} at {exp.company} ({exp.duration})" + (f" - Achievements: {len(exp.achievements or [])} items" if exp.achievements else " - No achievements listed") for exp in cv.experience]) if cv.experience else "  None"}

{cv_json_structure}
"""
    
    # Thông tin jobs đã apply (nếu có)
    jobs_info = ""
    required_skills_from_jobs = []
    if jobs_list:
        for job in jobs_list:
            required_skills_from_jobs.extend(job.required_skills)
        required_skills_from_jobs = list(set(required_skills_from_jobs))
        
        jobs_info = f"""
Jobs Applied/Interested ({len(jobs_list)} jobs):
{chr(10).join([f"  - {job.title} at {job.company}: requires {', '.join(job.required_skills[:5])}" for job in jobs_list[:10]])}

All Required Skills from Jobs: {', '.join(required_skills_from_jobs[:20])}
"""
    else:
        jobs_info = "\nNo job interaction history available."
    
    prompt = f"""You are an expert HR consultant. Evaluate this CV and provide SPECIFIC EDIT SUGGESTIONS for the CV JSON.

{cv_info}
{jobs_info}

TASK 1: Score each criterion from 0-100:
1. SKILLS_SCORE: Quality and quantity of skills (0-30: Few, 31-60: Moderate, 61-80: Good, 81-100: Excellent)
2. EXPERIENCE_SCORE: Work experience quality (0-30: Entry, 31-60: Some, 61-80: Good, 81-100: Extensive)
3. EDUCATION_SCORE: Educational background (0-30: Basic, 31-60: Bachelor's, 61-80: Good uni, 81-100: Advanced)
4. COMPLETENESS_SCORE: How complete is the CV?
5. JOB_ALIGNMENT_SCORE: Match with jobs applied (if no history: 50-70 based on marketability)
6. PRESENTATION_SCORE: CV quality and professionalism

TASK 2: Provide SPECIFIC EDITS to improve the CV JSON. For each edit, specify:
- field_path: The exact JSON path (e.g., "skills", "summary", "experience[0].achievements", "certifications")
- action: "add" (add new item), "update" (modify existing), "remove" (delete), "rewrite" (completely rewrite)
- current_value: Current value (if updating/rewriting)
- suggested_value: The exact new value to use
- reason: Why this change will improve the CV
- priority: "high", "medium", or "low"
- impact_score: Estimated score increase (1-10 points)

Return ONLY valid JSON:
{{
    "breakdown": {{
        "skills_score": <0-100>,
        "experience_score": <0-100>,
        "education_score": <0-100>,
        "completeness_score": <0-100>,
        "job_alignment_score": <0-100>,
        "presentation_score": <0-100>
    }},
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2", "weakness3"],
    "recommendations": ["rec1", "rec2", "rec3", "rec4", "rec5"],
    "cv_edits": [
        {{
            "field_path": "skills",
            "action": "add",
            "current_value": null,
            "suggested_value": "Docker",
            "reason": "Docker is required by 3 of the jobs you applied for",
            "priority": "high",
            "impact_score": 5
        }},
        {{
            "field_path": "summary",
            "action": "rewrite",
            "current_value": "Current summary text...",
            "suggested_value": "Results-driven Backend Developer with 3+ years of experience...",
            "reason": "Summary should highlight key achievements and be more specific",
            "priority": "high",
            "impact_score": 8
        }},
        {{
            "field_path": "experience[0].achievements",
            "action": "add",
            "current_value": null,
            "suggested_value": "Reduced API response time by 40% through query optimization",
            "reason": "Quantified achievements significantly improve CV impact",
            "priority": "high",
            "impact_score": 7
        }}
    ]
}}

IMPORTANT: 
- Provide 5-10 specific cv_edits
- Focus on high-impact changes first
- Be specific with suggested_value (provide actual text, not placeholders)
- Use correct field_path syntax for nested fields"""

    messages = [
        {"role": "system", "content": "Expert HR consultant. Evaluate CVs and provide specific, actionable edit suggestions. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    result = call_llm(messages, max_tokens=3000)
    return json.loads(result)


def calculate_grade(score: float) -> str:
    """Tính grade từ điểm số"""
    if score >= 90:
        return "A+"
    elif score >= 85:
        return "A"
    elif score >= 80:
        return "A-"
    elif score >= 75:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 65:
        return "B-"
    elif score >= 60:
        return "C+"
    elif score >= 55:
        return "C"
    elif score >= 50:
        return "C-"
    elif score >= 45:
        return "D+"
    elif score >= 40:
        return "D"
    else:
        return "F"


# ============================================================================
# ROUTE 4: EVALUATE CV WITH TARGET JD + SIMILAR JDs
# ============================================================================

@app.post("/evaluate/with-jd", response_model=EvaluateResponse)
async def evaluate_cv_with_jd(request: EvaluateWithJDRequest):
    """
    Đánh giá CV dựa trên:
    - Target JD (chú trọng chính, đánh giá phù hợp với JD này)
    - Similar JDs (tham khảo thêm các skills/requirements tương tự)
    
    Flow theo diagram:
    1. Thu thập & chuẩn hóa dữ liệu đầu vào
    2. Trích xuất kỹ năng từ CV và JD
    3. Mapping vào ontology kỹ năng
    4. Tính skill gap (CV vs JD)
    5. Xây dựng ngữ cảnh CV + JD + skill gap
    6. Truy hồi tri thức liên quan (RAG)
    7. Gọi LLM sinh gợi ý chỉnh sửa CV
    8. Hậu xử lý & chuẩn hóa output
    
    Output: overall_score (0-100), grade (A-F), skill_gap, cv_edits
    """
    logger.info(f"📊 Evaluating CV with Target JD: {request.cv.name}")
    logger.info(f"   Target JD: {request.target_jd.title} at {request.target_jd.company}")
    logger.info(f"   Similar JDs: {len(request.similar_jds or [])}")
    
    try:
        cv = request.cv
        target_jd = request.target_jd
        similar_jds = request.similar_jds or []
        
        # ===== STEP 1-4: SKILL GAP ANALYSIS =====
        skill_gap_info = None
        rag_context = ""
        
        if SKILL_MODULES_AVAILABLE:
            logger.info("   📌 Running skill gap analysis...")
            
            # Collect all JD skills (target + similar)
            all_jd_skills = list(target_jd.required_skills)
            for sjd in similar_jds:
                all_jd_skills.extend(sjd.required_skills)
            
            # Calculate skill gap
            gap_result = calculate_skill_gap(
                cv_skills=cv.skills,
                jd_skills=target_jd.required_skills,
                include_similar_jds_skills=all_jd_skills
            )
            
            logger.info(f"   ✅ Skill gap: {gap_result.match_percentage}% match, {len(gap_result.missing_skills)} missing")
            
            # Create skill gap info for response
            skill_gap_info = SkillGapInfo(
                match_percentage=gap_result.match_percentage,
                gap_severity=gap_result.gap_severity,
                matching_skills=gap_result.matching_skills,
                missing_skills=gap_result.missing_skills,
                extra_skills=gap_result.extra_skills[:10],  # Limit to 10
                high_priority_missing=gap_result.high_priority_missing,
                quick_wins=gap_result.quick_wins
            )
            
            # ===== STEP 5-6: BUILD RAG CONTEXT =====
            logger.info("   📚 Building RAG context...")
            try:
                rag_context = get_rag_context_for_evaluation(
                    cv_skills=cv.skills,
                    jd_skills=target_jd.required_skills,
                    jd_title=target_jd.title,
                    skill_gap=gap_result,
                    use_embeddings=False  # Start with simple context, set True for full RAG
                )
            except Exception as rag_error:
                logger.warning(f"   ⚠️ RAG context failed: {rag_error}")
                rag_context = format_skill_gap_for_prompt(gap_result)
        
        # ===== STEP 7: CALL LLM =====
        logger.info("   🤖 Calling LLM for evaluation...")
        evaluation = evaluate_cv_with_target_jd_enhanced(
            cv, target_jd, similar_jds, rag_context
        )
        
        # Tính điểm tổng hợp (weighted average)
        breakdown = evaluation["breakdown"]
        
        # Trọng số - skill alignment quan trọng hơn khi có explicit gap analysis
        weights = {
            "skills": 0.25,
            "experience": 0.20,
            "education": 0.10,
            "completeness": 0.10,
            "job_alignment": 0.25,
            "presentation": 0.10
        }
        
        overall_score = (
            breakdown["skills_score"] * weights["skills"] +
            breakdown["experience_score"] * weights["experience"] +
            breakdown["education_score"] * weights["education"] +
            breakdown["completeness_score"] * weights["completeness"] +
            breakdown["job_alignment_score"] * weights["job_alignment"] +
            breakdown["presentation_score"] * weights["presentation"]
        )
        
        grade = calculate_grade(overall_score)
        
        logger.info(f"✅ Evaluation complete: {overall_score:.1f}/100 (Grade: {grade})")
        
        # ===== STEP 8: POST-PROCESS CV EDITS =====
        cv_edits_raw = evaluation.get("cv_edits", [])
        cv_edits = []
        for edit in cv_edits_raw:
            suggested_val = edit.get("suggested_value", "")
            if isinstance(suggested_val, (list, dict)):
                suggested_val = json.dumps(suggested_val, ensure_ascii=False)
            elif suggested_val is None:
                suggested_val = ""
            else:
                suggested_val = str(suggested_val)
            
            current_val = edit.get("current_value")
            if isinstance(current_val, (list, dict)):
                current_val = json.dumps(current_val, ensure_ascii=False)
            elif current_val is not None:
                current_val = str(current_val)
            
            try:
                cv_edits.append(
                    CVEdit(
                        field_path=edit.get("field_path", ""),
                        action=edit.get("action", "add"),
                        current_value=current_val,
                        suggested_value=suggested_val,
                        reason=edit.get("reason", ""),
                        priority=edit.get("priority", "medium"),
                        impact_score=edit.get("impact_score")
                    )
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse cv_edit: {e}. Skipping.")
                continue
        
        logger.info(f"   CV Edits suggested: {len(cv_edits)}")
        
        return EvaluateResponse(
            success=True,
            cv_name=cv.name,
            overall_score=round(overall_score, 1),
            grade=grade,
            score_breakdown=ScoreBreakdown(
                skills_score=breakdown["skills_score"],
                experience_score=breakdown["experience_score"],
                education_score=breakdown["education_score"],
                completeness_score=breakdown["completeness_score"],
                job_alignment_score=breakdown["job_alignment_score"],
                presentation_score=breakdown["presentation_score"]
            ),
            strengths=evaluation["strengths"],
            weaknesses=evaluation["weaknesses"],
            recommendations=evaluation["recommendations"],
            cv_edits=cv_edits,
            skill_gap=skill_gap_info,  # NEW: Include skill gap analysis
            jobs_analyzed=1 + len(similar_jds),
            deterministic=True
        )
        
    except Exception as e:
        logger.error(f"❌ Evaluation error: {e}")
        import traceback
        traceback.print_exc()
        return EvaluateResponse(
            success=False,
            cv_name=request.cv.name,
            overall_score=0,
            grade="F",
            score_breakdown=ScoreBreakdown(
                skills_score=0, experience_score=0, education_score=0,
                completeness_score=0, job_alignment_score=0, presentation_score=0
            ),
            strengths=[],
            weaknesses=[],
            recommendations=[],
            cv_edits=[],
            skill_gap=None,
            jobs_analyzed=0,
            error=str(e)
        )


def evaluate_cv_with_target_jd_enhanced(
    cv: CV, 
    target_jd: JobDescription, 
    similar_jds: List[JobDescription],
    rag_context: str = ""
) -> Dict:
    """
    Đánh giá CV với focus vào target JD, tham khảo similar JDs cho additional skills.
    
    Enhanced version với RAG context từ skill ontology và knowledge base.
    
    - Target JD: Đánh giá chính, skills match, requirements match
    - Similar JDs: Tham khảo thêm skills tương tự, requirements phổ biến trong ngành
    - RAG Context: Knowledge từ skill ontology, career paths, resume tips
    """
    
    # Chuẩn bị thông tin CV chi tiết
    cv_json_structure = f"""
CV JSON Structure:
{{
  "name": "{cv.name}",
  "email": "{cv.email}",
  "phone": "{cv.phone or 'null'}",
  "summary": "{(cv.summary or 'null')[:100]}...",
  "skills": {json.dumps(cv.skills[:10] if cv.skills else [], ensure_ascii=False)}{"..." if len(cv.skills) > 10 else ""},
  "education": [
{chr(10).join([f'    {{"degree": "{edu.degree}", "institution": "{edu.institution}", "gpa": {edu.gpa or "null"}}}' for edu in cv.education[:3]])}
  ],
  "experience": [
{chr(10).join([f'    {{"title": "{exp.title}", "company": "{exp.company}", "duration": "{exp.duration}", "responsibilities": {len(exp.responsibilities)} items, "achievements": {len(exp.achievements or [])} items}}' for exp in cv.experience[:3]])}
  ],
  "certifications": {json.dumps(cv.certifications[:5] if cv.certifications else [], ensure_ascii=False)},
  "languages": {json.dumps(cv.languages[:5] if cv.languages else [], ensure_ascii=False)}
}}
"""

    cv_info = f"""
CV Information:
- Name: {cv.name}
- Email: {cv.email}
- Phone: {cv.phone or 'Not provided'}
- Summary: {cv.summary or 'Not provided'}
- Skills: {', '.join(cv.skills) if cv.skills else 'None listed'}
- Number of skills: {len(cv.skills)}
- Education entries: {len(cv.education)}
- Experience entries: {len(cv.experience)}
- Certifications: {len(cv.certifications or [])}
- Languages: {len(cv.languages or [])}

Education Details:
{chr(10).join([f"  - {edu.degree} at {edu.institution}" + (f" (GPA: {edu.gpa})" if edu.gpa else "") for edu in cv.education]) if cv.education else "  None"}

Experience Details:
{chr(10).join([f"  - {exp.title} at {exp.company} ({exp.duration})" + (f" - Achievements: {len(exp.achievements or [])} items" if exp.achievements else " - No achievements listed") for exp in cv.experience]) if cv.experience else "  None"}

{cv_json_structure}
"""
    
    # ===== TARGET JD (CHÍNH - CHÚ TRỌNG NHẤT) =====
    target_jd_info = f"""
===== TARGET JOB DESCRIPTION (PRIMARY - FOCUS ON THIS) =====
Title: {target_jd.title}
Company: {target_jd.company}

REQUIRED SKILLS (MUST HAVE):
{chr(10).join([f"  ★ {skill}" for skill in target_jd.required_skills])}

REQUIREMENTS:
{chr(10).join([f"  - {req}" for req in target_jd.requirements])}

RESPONSIBILITIES:
{chr(10).join([f"  - {resp}" for resp in target_jd.responsibilities[:5]])}

PREFERRED QUALIFICATIONS:
{chr(10).join([f"  - {qual}" for qual in (target_jd.preferred_qualifications or [])[:5]]) or "  None specified"}
"""
    
    # ===== SIMILAR JDs (THAM KHẢO) =====
    similar_jds_info = ""
    all_similar_skills = []
    all_similar_requirements = []
    
    if similar_jds:
        for jd in similar_jds:
            all_similar_skills.extend(jd.required_skills)
            all_similar_requirements.extend(jd.requirements[:3])
        
        # Deduplicate
        all_similar_skills = list(set(all_similar_skills))
        all_similar_requirements = list(set(all_similar_requirements))
        
        similar_jds_info = f"""
===== SIMILAR JOB DESCRIPTIONS (FOR REFERENCE ONLY) =====
These similar JDs provide additional context on common skills and requirements in this field.
Use these to identify additional valuable skills the candidate might need.

Similar Positions ({len(similar_jds)} jobs):
{chr(10).join([f"  • {jd.title} at {jd.company} - Skills: {', '.join(jd.required_skills[:5])}" for jd in similar_jds[:5]])}

Common Skills across Similar JDs (for reference):
{', '.join(all_similar_skills[:15])}

Common Requirements across Similar JDs (for reference):
{chr(10).join([f"  - {req}" for req in all_similar_requirements[:5]])}
"""
    else:
        similar_jds_info = "\nNo similar JDs provided for reference."
    
    # ===== RAG CONTEXT (KNOWLEDGE FROM ONTOLOGY) =====
    rag_section = ""
    if rag_context:
        rag_section = f"""
{rag_context}
"""
    
    prompt = f"""You are an expert HR consultant. Evaluate this CV PRIMARILY against the TARGET JOB DESCRIPTION.
The similar JDs are only for REFERENCE to identify additional relevant skills in the field.

{cv_info}

{target_jd_info}

{similar_jds_info}
{rag_section}
===== EVALUATION INSTRUCTIONS =====

PRIORITY ORDER:
1. **TARGET JD is PRIMARY** - Evaluate CV match against target JD's requirements, skills, responsibilities
2. **SKILL GAP ANALYSIS** - Use the skill gap data above to identify exact missing skills
3. **KNOWLEDGE BASE** - Use the skill knowledge to provide accurate learning paths and CV tips
4. **Similar JDs are SECONDARY** - Only use to identify additional skills that could strengthen the candidate

TASK 1: Score each criterion from 0-100:
1. SKILLS_SCORE: How well do the CV skills match the TARGET JD required skills? (Also note gaps from similar JDs)
2. EXPERIENCE_SCORE: Does experience match TARGET JD requirements?
3. EDUCATION_SCORE: Does education meet TARGET JD requirements?
4. COMPLETENESS_SCORE: How complete is the CV overall?
5. JOB_ALIGNMENT_SCORE: Overall fit with TARGET JD (weight this heavily!)
6. PRESENTATION_SCORE: CV quality and professionalism

TASK 2: Provide SPECIFIC EDITS to improve CV for the TARGET JD:
- Focus edits on skills/experience gaps for the TARGET JD
- Suggest additional skills from similar JDs that would strengthen the application
- Be specific with field_path, action, suggested_value

Return ONLY valid JSON:
{{
    "breakdown": {{
        "skills_score": <0-100>,
        "experience_score": <0-100>,
        "education_score": <0-100>,
        "completeness_score": <0-100>,
        "job_alignment_score": <0-100>,
        "presentation_score": <0-100>
    }},
    "strengths": ["strength1 (specific to target JD match)", "strength2", "strength3"],
    "weaknesses": ["weakness1 (gap vs target JD)", "weakness2", "weakness3"],
    "recommendations": ["rec1 (priority for target JD)", "rec2", "rec3", "rec4", "rec5"],
    "cv_edits": [
        {{
            "field_path": "skills",
            "action": "add",
            "current_value": null,
            "suggested_value": "skill_from_target_jd",
            "reason": "This skill is required by the target JD: {target_jd.title}",
            "priority": "high",
            "impact_score": 8
        }},
        {{
            "field_path": "summary",
            "action": "rewrite",
            "current_value": "...",
            "suggested_value": "Tailored summary for {target_jd.title} role...",
            "reason": "Summary should be tailored for the target position",
            "priority": "high",
            "impact_score": 7
        }},
        {{
            "field_path": "skills",
            "action": "add",
            "current_value": null,
            "suggested_value": "skill_from_similar_jds",
            "reason": "Common skill in similar roles that would strengthen your profile",
            "priority": "medium",
            "impact_score": 4
        }}
    ]
}}

IMPORTANT:
- Provide 5-10 specific cv_edits
- HIGH priority edits should address TARGET JD gaps
- MEDIUM priority edits can include skills from similar JDs
- Be specific with suggested_value (provide actual text)
- Strengths/weaknesses should specifically reference TARGET JD match"""

    messages = [
        {"role": "system", "content": f"Expert HR consultant evaluating CV fit for '{target_jd.title}' position. Focus on target JD, use similar JDs only as reference. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    result = call_llm(messages, max_tokens=3500)
    return json.loads(result)


# ============================================================================
# Health Check & Info Routes
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": "LGIR CV Matching API - Production",
        "version": "3.2.0",
        "status": "active",
        "routes": {
            "parse_pdf": "POST /parse/pdf - Upload PDF CV to parse",
            "parse_text": "POST /parse/text - Parse CV text",
            "score": "POST /score - Score CV matching with multiple jobs",
            "evaluate": "POST /evaluate - Evaluate CV → ONE overall score (0-100)",
            "evaluate_with_jd": "POST /evaluate/with-jd - Evaluate CV with target JD + similar JDs",
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
    port = int(os.getenv('PORT', 10800))
    
    print("="*80)
    print("🚀 LGIR CV Matching API - Production Server")
    print("="*80)
    print(f"\n📍 Running on: http://0.0.0.0:{port}")
    print(f"📚 API Docs: http://0.0.0.0:{port}/docs")
    print("\n🔧 Routes:")
    print("   POST /parse/pdf       - Parse PDF CV")
    print("   POST /parse/text      - Parse text CV")
    print("   POST /score           - Score CV matching with jobs")
    print("   POST /evaluate        - Evaluate CV → ONE score")
    print("   POST /evaluate/with-jd - Evaluate CV with target JD + similar JDs (NEW!)")
    print("   GET  /health          - Health check")
    print("\n" + "="*80 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

