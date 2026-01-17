"""
RAG Knowledge System for CV Recommendation
===========================================

Module này cung cấp:
1. Vector store cho skill knowledge
2. Semantic search để retrieve relevant knowledge
3. Context building cho LLM prompts
4. Integration với skill ontology

Cách hoạt động:
1. Load knowledge từ ontology + career paths + resume tips
2. Embed documents vào vectors (OpenAI embeddings)
3. Query: embed query → tìm similar documents → build context
"""

import json
import os
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass

try:
    import openai
    from dotenv import load_dotenv
    load_dotenv()
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from skill_ontology import get_all_skills, get_skill, Skill
from skill_processor import SkillGapAnalysis, format_skill_gap_for_prompt

logger = logging.getLogger(__name__)


# ============================================================================
# CAREER PATHS KNOWLEDGE
# ============================================================================

CAREER_PATHS = [
    {
        "id": "backend_junior",
        "path": "Backend Developer",
        "level": "Junior (0-2 năm)",
        "required_skills": ["Python/Java/Node.js", "SQL", "REST API", "Git"],
        "salary_range": "8-18 triệu VND",
        "focus": "Học fundamentals, viết clean code, làm quen team workflow",
        "next_step": "Học Docker, Testing, CI/CD basics để lên Mid-level"
    },
    {
        "id": "backend_mid",
        "path": "Backend Developer", 
        "level": "Mid-level (2-4 năm)",
        "required_skills": ["+ Database optimization", "+ Docker", "+ Testing", "+ CI/CD"],
        "salary_range": "18-35 triệu VND",
        "focus": "Feature ownership, code review, mentoring junior",
        "next_step": "Học System Design, Microservices, Cloud để lên Senior"
    },
    {
        "id": "backend_senior",
        "path": "Backend Developer",
        "level": "Senior (4-7 năm)",
        "required_skills": ["+ System Design", "+ Microservices", "+ Cloud (AWS/GCP)", "+ Kubernetes"],
        "salary_range": "35-60 triệu VND",
        "focus": "Technical leadership, architecture decisions",
        "next_step": "Có thể chuyển sang Staff Engineer hoặc Engineering Manager"
    },
    {
        "id": "frontend_junior",
        "path": "Frontend Developer",
        "level": "Junior (0-2 năm)",
        "required_skills": ["HTML/CSS", "JavaScript", "React/Vue", "Git"],
        "salary_range": "8-15 triệu VND",
        "focus": "Học framework, responsive design, basic UX",
        "next_step": "Học TypeScript, State Management, Testing"
    },
    {
        "id": "frontend_senior",
        "path": "Frontend Developer",
        "level": "Senior (4+ năm)",
        "required_skills": ["+ Architecture", "+ SSR/SSG", "+ Design Systems", "+ Performance"],
        "salary_range": "30-50 triệu VND",
        "focus": "Frontend architecture, DX improvement, mentoring",
        "next_step": "Có thể chuyển sang Tech Lead hoặc Full-stack"
    },
    {
        "id": "devops_mid",
        "path": "DevOps Engineer",
        "level": "Mid-level (2-4 năm)",
        "required_skills": ["Linux", "Docker", "Kubernetes", "CI/CD", "Cloud", "Terraform"],
        "salary_range": "25-45 triệu VND",
        "focus": "Infrastructure design, reliability, automation",
        "next_step": "Học Platform Engineering, Security, Multi-cloud"
    },
    {
        "id": "fullstack_senior",
        "path": "Full-Stack Developer",
        "level": "Senior (4+ năm)",
        "required_skills": ["Frontend (React/Vue)", "Backend (Node/Python)", "Database", "DevOps basics", "System Design"],
        "salary_range": "40-70 triệu VND",
        "focus": "End-to-end feature ownership, startups love full-stack",
        "next_step": "CTO track hoặc chuyên sâu một mảng"
    }
]


# ============================================================================
# RESUME TIPS KNOWLEDGE
# ============================================================================

RESUME_TIPS = [
    {
        "id": "quantify",
        "category": "Content",
        "title": "Luôn quantify achievements",
        "description": "Thay vì 'Improved performance', viết 'Reduced API response time by 40% from 500ms to 300ms'",
        "examples": [
            "Bad: Developed APIs for the project",
            "Good: Developed 15+ RESTful APIs serving 10K+ daily requests with 99.9% uptime"
        ],
        "impact": "high"
    },
    {
        "id": "action_verbs",
        "category": "Content",
        "title": "Sử dụng action verbs mạnh",
        "description": "Bắt đầu bullet point bằng: Developed, Implemented, Designed, Led, Optimized, Architected",
        "examples": [
            "Bad: Was responsible for backend development",
            "Good: Architected microservices backend handling 1M+ transactions/day"
        ],
        "impact": "high"
    },
    {
        "id": "tailored",
        "category": "Strategy",
        "title": "Customize CV cho từng job",
        "description": "Điều chỉnh skills và achievements để match JD. Đưa relevant experience lên đầu.",
        "examples": [
            "Nếu JD yêu cầu AWS → đưa AWS lên đầu skills",
            "Nếu JD là fintech → highlight financial projects"
        ],
        "impact": "very_high"
    },
    {
        "id": "keywords",
        "category": "ATS",
        "title": "Sử dụng keywords từ JD",
        "description": "ATS systems scan keywords. Copy exact terms từ JD vào CV.",
        "examples": [
            "JD: 'CI/CD pipelines' → CV: 'Implemented CI/CD pipelines using GitHub Actions'",
            "JD: 'Microservices' → CV: 'Designed microservices architecture...'"
        ],
        "impact": "very_high"
    },
    {
        "id": "projects",
        "category": "Portfolio",
        "title": "Include side projects và open source",
        "description": "Side projects show passion. GitHub profile với contributions rất valuable.",
        "examples": [
            "Contributed to popular open source libraries",
            "Built personal project với real users"
        ],
        "impact": "medium"
    },
    {
        "id": "skills_format",
        "category": "Format",
        "title": "Format skills section đúng cách",
        "description": "Nhóm skills theo category, liệt kê cụ thể frameworks/tools.",
        "examples": [
            "Bad: Python, JavaScript, databases",
            "Good: Backend: Python (Django, FastAPI) | Frontend: React, TypeScript | DB: PostgreSQL, Redis"
        ],
        "impact": "medium"
    },
    {
        "id": "summary",
        "category": "Content",
        "title": "Viết summary mạnh mẽ",
        "description": "Summary 2-3 câu highlight years of exp, main skills, notable achievements.",
        "examples": [
            "Bad: I am a developer looking for opportunities",
            "Good: Backend Engineer with 4+ years building scalable APIs. Led migration to microservices reducing latency 50%."
        ],
        "impact": "high"
    },
    {
        "id": "achievements_not_duties",
        "category": "Content", 
        "title": "Focus achievements, không phải duties",
        "description": "Đừng list job duties - list những gì bạn achieved và impact.",
        "examples": [
            "Bad: Responsible for maintaining backend systems",
            "Good: Improved system reliability from 95% to 99.9% uptime through automated monitoring"
        ],
        "impact": "very_high"
    }
]


# ============================================================================
# VECTOR STORE (Simple In-Memory)
# ============================================================================

@dataclass
class Document:
    """Document trong vector store"""
    id: str
    content: str
    doc_type: str  # "skill", "career_path", "resume_tip"
    metadata: Dict


class SimpleVectorStore:
    """
    Simple in-memory vector store.
    Sử dụng OpenAI embeddings + cosine similarity.
    """
    
    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings: List[List[float]] = []
        self.is_initialized = False
        self._client = None
    
    def _get_client(self):
        """Lazy load OpenAI client"""
        if self._client is None and HAS_OPENAI:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self._client = openai.OpenAI(api_key=api_key)
        return self._client
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding từ OpenAI"""
        client = self._get_client()
        if not client:
            logger.warning("OpenAI client not available")
            return None
            
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]  # Limit text length
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    
    def add_document(self, doc: Document):
        """Add document với embedding"""
        embedding = self._get_embedding(doc.content)
        if embedding:
            self.documents.append(doc)
            self.embeddings.append(embedding)
    
    def search(self, query: str, top_k: int = 5, doc_type: Optional[str] = None) -> List[Tuple[Document, float]]:
        """
        Search documents tương tự với query.
        
        Args:
            query: Search query
            top_k: Number of results
            doc_type: Filter by document type (optional)
        """
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        results = []
        for i, doc_embedding in enumerate(self.embeddings):
            doc = self.documents[i]
            
            # Filter by type if specified
            if doc_type and doc.doc_type != doc_type:
                continue
                
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            results.append((doc, similarity))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def initialize(self):
        """
        Initialize vector store với knowledge base.
        Load skills, career paths, và resume tips.
        """
        if self.is_initialized:
            logger.info("Vector store already initialized")
            return
        
        logger.info("📚 Initializing RAG Vector Store...")
        
        # 1. Load skills từ ontology
        all_skills = get_all_skills()
        for skill in all_skills:
            content = f"""
Skill: {skill.name}
Category: {skill.category.value}
Description: {skill.description}
Related Skills: {', '.join(skill.related_skills)}
Learning Path: {skill.learning_path}
Best Practices: {'; '.join(skill.best_practices)}
CV Tips: {skill.cv_tips}
Market Demand: {skill.market_demand.value}
Salary Range: {skill.salary_range_vnd}
"""
            self.add_document(Document(
                id=f"skill_{skill.id}",
                content=content,
                doc_type="skill",
                metadata={
                    "name": skill.name,
                    "category": skill.category.value,
                    "market_demand": skill.market_demand.value
                }
            ))
        
        # 2. Load career paths
        for path in CAREER_PATHS:
            content = f"""
Career Path: {path['path']} - {path['level']}
Required Skills: {', '.join(path['required_skills'])}
Salary Range: {path['salary_range']}
Focus: {path['focus']}
Next Step: {path['next_step']}
"""
            self.add_document(Document(
                id=f"career_{path['id']}",
                content=content,
                doc_type="career_path",
                metadata=path
            ))
        
        # 3. Load resume tips
        for tip in RESUME_TIPS:
            content = f"""
Resume Tip: {tip['title']}
Category: {tip['category']}
Description: {tip['description']}
Examples: {'; '.join(tip['examples'])}
Impact: {tip['impact']}
"""
            self.add_document(Document(
                id=f"tip_{tip['id']}",
                content=content,
                doc_type="resume_tip",
                metadata=tip
            ))
        
        self.is_initialized = True
        logger.info(f"✅ Loaded {len(self.documents)} documents into vector store")


# Global instance
_vector_store: Optional[SimpleVectorStore] = None


def get_vector_store() -> SimpleVectorStore:
    """Get or create vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = SimpleVectorStore()
    return _vector_store


# ============================================================================
# RAG RETRIEVAL FUNCTIONS
# ============================================================================

def retrieve_skill_knowledge(
    skill_names: List[str],
    top_k: int = 5
) -> List[Dict]:
    """
    Retrieve knowledge về specific skills.
    """
    results = []
    
    for skill_name in skill_names[:10]:  # Limit to 10 skills
        skill = get_skill(skill_name)
        if skill:
            results.append({
                "skill": skill.name,
                "category": skill.category.value,
                "description": skill.description,
                "learning_path": skill.learning_path,
                "best_practices": skill.best_practices,
                "cv_tips": skill.cv_tips,
                "market_demand": skill.market_demand.value,
                "related_skills": skill.related_skills[:5]
            })
    
    return results


def retrieve_relevant_knowledge(
    query: str,
    top_k: int = 8
) -> List[Tuple[Document, float]]:
    """
    Retrieve relevant knowledge using semantic search.
    
    Args:
        query: Natural language query
        top_k: Number of results to return
    
    Returns:
        List of (Document, similarity_score) tuples
    """
    store = get_vector_store()
    
    if not store.is_initialized:
        store.initialize()
    
    return store.search(query, top_k=top_k)


def retrieve_career_advice(
    target_role: str,
    current_skills: List[str]
) -> List[Dict]:
    """
    Retrieve career path advice based on target role and current skills.
    """
    advice = []
    target_lower = target_role.lower()
    
    for path in CAREER_PATHS:
        if any(word in target_lower for word in path['path'].lower().split()):
            advice.append(path)
    
    return advice


def retrieve_resume_tips(
    context: str = "general",
    top_k: int = 5
) -> List[Dict]:
    """
    Retrieve relevant resume tips.
    """
    if context == "general":
        # Return high impact tips
        return [tip for tip in RESUME_TIPS if tip['impact'] in ['very_high', 'high']][:top_k]
    
    # Use semantic search for specific context
    store = get_vector_store()
    if not store.is_initialized:
        store.initialize()
    
    results = store.search(context, top_k=top_k, doc_type="resume_tip")
    return [r[0].metadata for r in results]


# ============================================================================
# CONTEXT BUILDING FOR LLM
# ============================================================================

def build_rag_context(
    cv_skills: List[str],
    jd_skills: List[str],
    target_role: str,
    skill_gap: SkillGapAnalysis
) -> str:
    """
    Build comprehensive RAG context cho LLM prompt.
    
    Kết hợp:
    1. Skill gap analysis
    2. Skill knowledge cho missing skills
    3. Career path advice
    4. Resume tips
    """
    context_parts = []
    
    # 1. Skill Gap Analysis
    context_parts.append(format_skill_gap_for_prompt(skill_gap))
    
    # 2. Knowledge about missing skills
    if skill_gap.missing_skills:
        context_parts.append("\n" + "="*50)
        context_parts.append("📚 KNOWLEDGE ABOUT MISSING SKILLS")
        context_parts.append("="*50)
        
        for skill_name in skill_gap.missing_skills[:5]:  # Top 5
            skill = get_skill(skill_name)
            if skill:
                context_parts.append(f"""
🔹 **{skill.name}** ({skill.category.value})
   Description: {skill.description}
   Learning Path: {skill.learning_path}
   CV Tip: {skill.cv_tips}
   Market Demand: {skill.market_demand.value}
""")
    
    # 3. Career Path Advice
    career_advice = retrieve_career_advice(target_role, cv_skills)
    if career_advice:
        context_parts.append("\n" + "="*50)
        context_parts.append("🎯 CAREER PATH ADVICE")
        context_parts.append("="*50)
        
        for path in career_advice[:2]:
            context_parts.append(f"""
📍 {path['path']} - {path['level']}
   Required: {', '.join(path['required_skills'])}
   Salary: {path['salary_range']}
   Focus: {path['focus']}
   Next: {path['next_step']}
""")
    
    # 4. Resume Tips
    context_parts.append("\n" + "="*50)
    context_parts.append("💡 RESUME IMPROVEMENT TIPS")
    context_parts.append("="*50)
    
    tips = retrieve_resume_tips("general", 3)
    for tip in tips:
        context_parts.append(f"""
📌 {tip['title']}
   {tip['description']}
   Example: {tip['examples'][0] if tip['examples'] else 'N/A'}
""")
    
    return "\n".join(context_parts)


def build_simple_context(
    missing_skills: List[str],
    matching_skills: List[str]
) -> str:
    """
    Build simple context without embeddings.
    Fallback khi không có OpenAI API key.
    """
    context_parts = [
        "="*50,
        "📚 SKILL KNOWLEDGE CONTEXT",
        "="*50,
        ""
    ]
    
    # Missing skills info
    if missing_skills:
        context_parts.append("❌ MISSING SKILLS TO LEARN:")
        for skill_name in missing_skills[:5]:
            skill = get_skill(skill_name)
            if skill:
                context_parts.append(f"""
   🔹 {skill.name}:
      - {skill.description[:100]}...
      - Learning: {skill.learning_path[:80]}...
      - CV Tip: {skill.cv_tips[:80]}...
""")
    
    # High impact tips
    context_parts.append("\n💡 KEY RESUME TIPS:")
    for tip in RESUME_TIPS[:3]:
        context_parts.append(f"   - {tip['title']}: {tip['description'][:80]}...")
    
    return "\n".join(context_parts)


# ============================================================================
# MAIN RETRIEVAL FUNCTION FOR API
# ============================================================================

def get_rag_context_for_evaluation(
    cv_skills: List[str],
    jd_skills: List[str],
    jd_title: str,
    skill_gap: SkillGapAnalysis,
    use_embeddings: bool = True
) -> str:
    """
    Main function để get RAG context cho API.
    
    Args:
        cv_skills: Skills từ CV
        jd_skills: Skills yêu cầu từ JD
        jd_title: Title của JD
        skill_gap: Kết quả skill gap analysis
        use_embeddings: Có dùng embeddings không (requires OpenAI API)
    
    Returns:
        Context string để thêm vào LLM prompt
    """
    if use_embeddings and HAS_OPENAI and os.getenv('OPENAI_API_KEY'):
        try:
            return build_rag_context(
                cv_skills=cv_skills,
                jd_skills=jd_skills,
                target_role=jd_title,
                skill_gap=skill_gap
            )
        except Exception as e:
            logger.warning(f"RAG with embeddings failed: {e}, falling back to simple context")
    
    # Fallback to simple context
    return build_simple_context(
        missing_skills=skill_gap.missing_skills,
        matching_skills=skill_gap.matching_skills
    )


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    from skill_processor import calculate_skill_gap
    
    print("="*60)
    print("RAG KNOWLEDGE SYSTEM TEST")
    print("="*60)
    
    # Test data
    cv_skills = ["Python", "Django", "PostgreSQL", "Git", "Docker", "REST API"]
    jd_skills = ["Python", "Go", "Kubernetes", "AWS", "Microservices", "Redis", "Kafka"]
    jd_title = "Senior Backend Developer"
    
    print(f"\nCV Skills: {cv_skills}")
    print(f"JD Skills: {jd_skills}")
    print(f"JD Title: {jd_title}")
    
    # Calculate skill gap
    print("\n1. Calculating skill gap...")
    gap = calculate_skill_gap(cv_skills, jd_skills)
    
    # Get simple context (no embeddings)
    print("\n2. Building simple context (no embeddings)...")
    simple_ctx = build_simple_context(gap.missing_skills, gap.matching_skills)
    print(simple_ctx)
    
    # Try RAG context with embeddings
    if HAS_OPENAI and os.getenv('OPENAI_API_KEY'):
        print("\n3. Building RAG context with embeddings...")
        try:
            rag_ctx = get_rag_context_for_evaluation(
                cv_skills, jd_skills, jd_title, gap, use_embeddings=True
            )
            print(rag_ctx)
        except Exception as e:
            print(f"   Error: {e}")
    else:
        print("\n3. Skipping embeddings test (no OpenAI API key)")
    
    # Test retrieve skill knowledge
    print("\n4. Retrieve skill knowledge for missing skills:")
    knowledge = retrieve_skill_knowledge(gap.missing_skills[:3])
    for k in knowledge:
        print(f"\n   {k['skill']}:")
        print(f"   - Category: {k['category']}")
        print(f"   - Demand: {k['market_demand']}")
