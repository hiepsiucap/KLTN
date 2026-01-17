"""
Skill Processor - Xử lý kỹ năng cho CV Recommendation
=====================================================

Module này cung cấp:
1. Skill Extraction - Trích xuất kỹ năng từ text
2. Skill Normalization - Chuẩn hóa tên kỹ năng
3. Skill Mapping - Map vào ontology
4. Skill Gap Calculation - Tính khoảng cách kỹ năng CV vs JD
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import Counter

from skill_ontology import (
    get_skill, 
    normalize_skill_name, 
    get_related_skills,
    get_all_skills,
    Skill,
    SkillCategory,
    MarketDemand
)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ExtractedSkill:
    """Kỹ năng được trích xuất từ text"""
    raw_name: str           # Tên gốc trong text
    normalized_name: str    # Tên đã chuẩn hóa
    category: str           # Category từ ontology
    confidence: float       # Độ tin cậy (0-1)
    source: str            # Nguồn: "cv" hoặc "jd"
    in_ontology: bool      # Có trong ontology không


@dataclass
class SkillGapAnalysis:
    """Kết quả phân tích skill gap"""
    matching_skills: List[str]      # Skills CV có và JD yêu cầu
    missing_skills: List[str]       # Skills JD yêu cầu mà CV không có
    extra_skills: List[str]         # Skills CV có mà JD không yêu cầu
    related_missing: Dict[str, List[str]]  # Skills liên quan đến missing skills mà CV có
    
    match_percentage: float         # % skills JD được cover
    gap_severity: str              # "low", "medium", "high", "critical"
    
    # Detailed breakdown
    matching_by_category: Dict[str, List[str]]
    missing_by_category: Dict[str, List[str]]
    
    # Priority skills
    high_priority_missing: List[str]    # Skills có market demand cao mà thiếu
    quick_wins: List[str]              # Skills dễ học có thể thêm nhanh


# ============================================================================
# SKILL EXTRACTION
# ============================================================================

def extract_skills_from_text(text: str, source: str = "unknown") -> List[ExtractedSkill]:
    """
    Trích xuất kỹ năng từ văn bản tự do.
    
    Sử dụng nhiều strategies:
    1. Exact match với ontology
    2. Pattern matching cho common formats
    3. Keyword detection
    """
    if not text:
        return []
    
    extracted = []
    seen = set()
    
    # Normalize text
    text_lower = text.lower()
    
    # Strategy 1: Match với tất cả skills trong ontology
    all_skills = get_all_skills()
    
    for skill in all_skills:
        # Check skill name
        if _find_skill_in_text(skill.name, text_lower):
            if skill.name not in seen:
                extracted.append(ExtractedSkill(
                    raw_name=skill.name,
                    normalized_name=skill.name,
                    category=skill.category.value,
                    confidence=1.0,
                    source=source,
                    in_ontology=True
                ))
                seen.add(skill.name)
        
        # Check aliases
        for alias in skill.aliases:
            if _find_skill_in_text(alias, text_lower):
                if skill.name not in seen:
                    extracted.append(ExtractedSkill(
                        raw_name=alias,
                        normalized_name=skill.name,
                        category=skill.category.value,
                        confidence=0.95,
                        source=source,
                        in_ontology=True
                    ))
                    seen.add(skill.name)
        
        # Check keywords
        for keyword in skill.keywords:
            if _find_skill_in_text(keyword, text_lower):
                if skill.name not in seen:
                    extracted.append(ExtractedSkill(
                        raw_name=keyword,
                        normalized_name=skill.name,
                        category=skill.category.value,
                        confidence=0.8,
                        source=source,
                        in_ontology=True
                    ))
                    seen.add(skill.name)
    
    # Strategy 2: Pattern matching cho các format phổ biến
    # "Skills: Python, Java, JavaScript"
    skills_section = re.findall(
        r'(?:skills?|technologies?|tech stack|kỹ năng)[\s:]+([^\n]+)',
        text_lower,
        re.IGNORECASE
    )
    
    for section in skills_section:
        # Split by common delimiters
        potential_skills = re.split(r'[,;|•·\-/]|\band\b', section)
        for ps in potential_skills:
            ps = ps.strip()
            if len(ps) > 1 and len(ps) < 30:  # Reasonable skill name length
                normalized = normalize_skill_name(ps)
                skill_obj = get_skill(normalized)
                
                if skill_obj and skill_obj.name not in seen:
                    extracted.append(ExtractedSkill(
                        raw_name=ps,
                        normalized_name=skill_obj.name,
                        category=skill_obj.category.value,
                        confidence=0.9,
                        source=source,
                        in_ontology=True
                    ))
                    seen.add(skill_obj.name)
                elif not skill_obj and ps not in seen:
                    # Unknown skill - still extract but flag
                    extracted.append(ExtractedSkill(
                        raw_name=ps,
                        normalized_name=ps.title(),
                        category="Other",
                        confidence=0.6,
                        source=source,
                        in_ontology=False
                    ))
                    seen.add(ps)
    
    return extracted


def _find_skill_in_text(skill_name: str, text: str) -> bool:
    """Check if skill name exists in text (word boundary aware)"""
    # Escape special regex chars
    escaped = re.escape(skill_name.lower())
    # Word boundary match (handle special chars like C++, C#)
    pattern = r'(?:^|[\s,;()\[\]{}])' + escaped + r'(?:[\s,;()\[\]{}]|$)'
    return bool(re.search(pattern, text))


def extract_skills_from_list(skills_list: List[str], source: str = "unknown") -> List[ExtractedSkill]:
    """
    Normalize và enrich một list skills có sẵn.
    Dùng khi skills đã được parse từ CV/JD JSON.
    """
    extracted = []
    seen = set()
    
    for raw_skill in skills_list:
        if not raw_skill or raw_skill.strip() == "":
            continue
            
        raw_skill = raw_skill.strip()
        
        # Try to find in ontology
        skill_obj = get_skill(raw_skill)
        
        if skill_obj:
            if skill_obj.name not in seen:
                extracted.append(ExtractedSkill(
                    raw_name=raw_skill,
                    normalized_name=skill_obj.name,
                    category=skill_obj.category.value,
                    confidence=1.0,
                    source=source,
                    in_ontology=True
                ))
                seen.add(skill_obj.name)
        else:
            # Not in ontology - keep original
            normalized = raw_skill.title()
            if normalized not in seen:
                extracted.append(ExtractedSkill(
                    raw_name=raw_skill,
                    normalized_name=normalized,
                    category="Other",
                    confidence=0.5,
                    source=source,
                    in_ontology=False
                ))
                seen.add(normalized)
    
    return extracted


# ============================================================================
# SKILL GAP CALCULATION
# ============================================================================

def calculate_skill_gap(
    cv_skills: List[str],
    jd_skills: List[str],
    include_similar_jds_skills: Optional[List[str]] = None
) -> SkillGapAnalysis:
    """
    Tính toán skill gap giữa CV và JD.
    
    Args:
        cv_skills: List skills từ CV
        jd_skills: List skills yêu cầu từ JD (target)
        include_similar_jds_skills: Skills từ similar JDs (optional, cho reference)
    
    Returns:
        SkillGapAnalysis với đầy đủ thông tin
    """
    # Extract và normalize skills
    cv_extracted = extract_skills_from_list(cv_skills, "cv")
    jd_extracted = extract_skills_from_list(jd_skills, "jd")
    
    # Create sets for comparison (normalized names)
    cv_normalized = {s.normalized_name.lower() for s in cv_extracted}
    jd_normalized = {s.normalized_name.lower() for s in jd_extracted}
    
    # Build lookup for original names
    cv_name_map = {s.normalized_name.lower(): s.normalized_name for s in cv_extracted}
    jd_name_map = {s.normalized_name.lower(): s.normalized_name for s in jd_extracted}
    
    # Calculate matching, missing, extra
    matching_lower = cv_normalized & jd_normalized
    missing_lower = jd_normalized - cv_normalized
    extra_lower = cv_normalized - jd_normalized
    
    # Check for related skills coverage
    related_missing = {}
    enhanced_matching = set(matching_lower)
    
    for missing in list(missing_lower):
        missing_skill = get_skill(missing)
        if missing_skill:
            # Check if CV has related skills
            related = set(s.lower() for s in missing_skill.related_skills)
            cv_has_related = related & cv_normalized
            
            if cv_has_related:
                related_missing[jd_name_map[missing]] = [cv_name_map[r] for r in cv_has_related]
    
    # Get actual names (not lowercase)
    matching_skills = [jd_name_map.get(m, m) for m in matching_lower]
    missing_skills = [jd_name_map.get(m, m) for m in missing_lower]
    extra_skills = [cv_name_map.get(e, e) for e in extra_lower]
    
    # Calculate match percentage
    if jd_skills:
        # Give partial credit for related skills
        base_match = len(matching_lower) / len(jd_normalized) * 100
        related_bonus = len(related_missing) * 0.3  # 30% credit for each related
        match_percentage = min(100, base_match + related_bonus)
    else:
        match_percentage = 100.0
    
    # Determine gap severity
    if match_percentage >= 80:
        gap_severity = "low"
    elif match_percentage >= 60:
        gap_severity = "medium"
    elif match_percentage >= 40:
        gap_severity = "high"
    else:
        gap_severity = "critical"
    
    # Categorize matching and missing
    matching_by_category = _categorize_skills(matching_skills)
    missing_by_category = _categorize_skills(missing_skills)
    
    # Identify high priority missing (high market demand)
    high_priority_missing = []
    for skill_name in missing_skills:
        skill = get_skill(skill_name)
        if skill and skill.market_demand in [MarketDemand.VERY_HIGH, MarketDemand.HIGH]:
            high_priority_missing.append(skill_name)
    
    # Identify quick wins (skills that are related to what CV already has)
    quick_wins = []
    for skill_name in missing_skills:
        skill = get_skill(skill_name)
        if skill:
            # If parent skills exist in CV, this is a quick win
            parent_in_cv = any(
                p.lower() in cv_normalized 
                for p in skill.parent_skills
            )
            if parent_in_cv:
                quick_wins.append(skill_name)
    
    return SkillGapAnalysis(
        matching_skills=matching_skills,
        missing_skills=missing_skills,
        extra_skills=extra_skills,
        related_missing=related_missing,
        match_percentage=round(match_percentage, 1),
        gap_severity=gap_severity,
        matching_by_category=matching_by_category,
        missing_by_category=missing_by_category,
        high_priority_missing=high_priority_missing,
        quick_wins=quick_wins
    )


def _categorize_skills(skill_names: List[str]) -> Dict[str, List[str]]:
    """Group skills by category"""
    categories = {}
    
    for skill_name in skill_names:
        skill = get_skill(skill_name)
        if skill:
            cat = skill.category.value
        else:
            cat = "Other"
        
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(skill_name)
    
    return categories


# ============================================================================
# SKILL ENRICHMENT
# ============================================================================

def enrich_skill_info(skill_name: str) -> Optional[Dict]:
    """
    Get enriched information about a skill from ontology.
    """
    skill = get_skill(skill_name)
    if not skill:
        return None
    
    return {
        "name": skill.name,
        "category": skill.category.value,
        "description": skill.description,
        "related_skills": skill.related_skills,
        "parent_skills": skill.parent_skills,
        "child_skills": skill.child_skills,
        "learning_path": skill.learning_path,
        "best_practices": skill.best_practices,
        "cv_tips": skill.cv_tips,
        "market_demand": skill.market_demand.value,
        "salary_range": skill.salary_range_vnd,
        "experience_level": skill.experience_level
    }


def get_learning_recommendations(missing_skills: List[str]) -> List[Dict]:
    """
    Tạo recommendations học tập cho các skills thiếu.
    """
    recommendations = []
    
    for skill_name in missing_skills:
        skill = get_skill(skill_name)
        if skill:
            recommendations.append({
                "skill": skill.name,
                "priority": "high" if skill.market_demand in [MarketDemand.VERY_HIGH, MarketDemand.HIGH] else "medium",
                "learning_path": skill.learning_path,
                "prerequisites": skill.parent_skills,
                "related_skills_to_learn": skill.related_skills[:3],
                "cv_tip": skill.cv_tips,
                "market_demand": skill.market_demand.value
            })
    
    # Sort by priority
    recommendations.sort(key=lambda x: 0 if x["priority"] == "high" else 1)
    
    return recommendations


# ============================================================================
# FORMAT OUTPUT FOR LLM/API
# ============================================================================

def format_skill_gap_for_prompt(gap: SkillGapAnalysis) -> str:
    """
    Format skill gap analysis thành string để thêm vào LLM prompt.
    """
    lines = [
        "=" * 50,
        "📊 SKILL GAP ANALYSIS",
        "=" * 50,
        "",
        f"📈 Match Percentage: {gap.match_percentage}%",
        f"🚦 Gap Severity: {gap.gap_severity.upper()}",
        "",
        f"✅ MATCHING SKILLS ({len(gap.matching_skills)}):",
    ]
    
    if gap.matching_skills:
        for cat, skills in gap.matching_by_category.items():
            lines.append(f"   [{cat}]: {', '.join(skills)}")
    else:
        lines.append("   None")
    
    lines.extend([
        "",
        f"❌ MISSING SKILLS ({len(gap.missing_skills)}):",
    ])
    
    if gap.missing_skills:
        for cat, skills in gap.missing_by_category.items():
            lines.append(f"   [{cat}]: {', '.join(skills)}")
    else:
        lines.append("   None - All required skills present!")
    
    if gap.high_priority_missing:
        lines.extend([
            "",
            f"🔴 HIGH PRIORITY MISSING (High Market Demand):",
            f"   {', '.join(gap.high_priority_missing)}"
        ])
    
    if gap.quick_wins:
        lines.extend([
            "",
            f"💡 QUICK WINS (Easy to learn based on existing skills):",
            f"   {', '.join(gap.quick_wins)}"
        ])
    
    if gap.related_missing:
        lines.extend([
            "",
            "🔗 RELATED SKILLS COVERAGE:",
        ])
        for missing, related in gap.related_missing.items():
            lines.append(f"   {missing} → CV has related: {', '.join(related)}")
    
    if gap.extra_skills:
        lines.extend([
            "",
            f"➕ EXTRA SKILLS IN CV ({len(gap.extra_skills)}):",
            f"   {', '.join(gap.extra_skills[:10])}{'...' if len(gap.extra_skills) > 10 else ''}"
        ])
    
    lines.append("")
    lines.append("=" * 50)
    
    return "\n".join(lines)


def format_skill_gap_json(gap: SkillGapAnalysis) -> Dict:
    """
    Format skill gap analysis as JSON for API response.
    """
    return {
        "match_percentage": gap.match_percentage,
        "gap_severity": gap.gap_severity,
        "matching_skills": gap.matching_skills,
        "missing_skills": gap.missing_skills,
        "extra_skills": gap.extra_skills,
        "high_priority_missing": gap.high_priority_missing,
        "quick_wins": gap.quick_wins,
        "related_coverage": gap.related_missing,
        "matching_by_category": gap.matching_by_category,
        "missing_by_category": gap.missing_by_category
    }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("SKILL PROCESSOR TEST")
    print("="*60)
    
    # Test data
    cv_skills = ["Python", "Django", "PostgreSQL", "Git", "Docker", "REST API", "Redis"]
    jd_skills = ["Python", "Go", "Kubernetes", "AWS", "Microservices", "Redis", "Kafka", "Docker"]
    
    print("\n1. CV Skills:", cv_skills)
    print("   JD Skills:", jd_skills)
    
    # Calculate gap
    print("\n2. Calculating Skill Gap...")
    gap = calculate_skill_gap(cv_skills, jd_skills)
    
    print(format_skill_gap_for_prompt(gap))
    
    # Test extraction from text
    print("\n3. Extract skills from text:")
    text = """
    Senior Backend Developer với 5 năm kinh nghiệm.
    Skills: Python, Django REST Framework, PostgreSQL, Docker, Kubernetes
    Có kinh nghiệm với microservices architecture và AWS.
    """
    
    extracted = extract_skills_from_text(text, "cv")
    print(f"   Found {len(extracted)} skills:")
    for skill in extracted:
        print(f"   - {skill.normalized_name} ({skill.category}, confidence: {skill.confidence})")
    
    # Test learning recommendations
    print("\n4. Learning Recommendations for missing skills:")
    recommendations = get_learning_recommendations(gap.missing_skills[:3])
    for rec in recommendations:
        print(f"\n   📚 {rec['skill']} (Priority: {rec['priority']})")
        print(f"      Path: {rec['learning_path'][:80]}...")
        print(f"      CV Tip: {rec['cv_tip'][:60]}...")

