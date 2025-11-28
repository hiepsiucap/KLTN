"""
Enhanced PDF CV Parser - Lấy TẤT CẢ thông tin chi tiết
Parse CV PDF → JSON đầy đủ để render lại CV
"""

import pdfplumber
import json
import openai
import os
from cv_models_enhanced import CVEnhanced, ContactInfo, Education, Experience, Certification, Language, Project, SkillCategory
from typing import Optional, Dict
from datetime import datetime

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in .env file")
openai.api_key = OPENAI_API_KEY


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract ALL text from PDF"""
    print(f"📄 Reading PDF: {pdf_path}")
    
    text_content = []
    with pdfplumber.open(pdf_path) as pdf:
        print(f"   Total pages: {len(pdf.pages)}")
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                text_content.append(f"--- PAGE {page_num} ---\n{text}")
                print(f"   ✓ Page {page_num}: {len(text)} characters")
    
    full_text = "\n\n".join(text_content)
    print(f"✅ Extracted {len(full_text)} total characters")
    return full_text


def parse_cv_enhanced(cv_text: str, filename: str = "unknown.pdf") -> CVEnhanced:
    """
    Parse CV text thành CVEnhanced model với TẤT CẢ details
    """
    print("\n🤖 Parsing CV with AI (Enhanced mode - getting ALL details)...")
    
    # Detailed prompt để lấy TẤT CẢ thông tin
    prompt = f"""You are an expert CV parser. Extract ALL information from this CV in maximum detail.
DO NOT skip or summarize anything. Include EVERY piece of information.

CV TEXT:
{cv_text}

Extract and return in this EXACT JSON format with ALL details:

{{
  "name": "Full name exactly as shown",
  "title": "Job title or professional title if shown",
  "contact": {{
    "email": "email address",
    "phone": "phone number with country code if shown",
    "address": "full address if shown",
    "city": "city",
    "country": "country",
    "linkedin": "LinkedIn URL if mentioned",
    "github": "GitHub URL if mentioned",
    "website": "personal website if mentioned",
    "portfolio": "portfolio URL if mentioned"
  }},
  "summary": "Complete professional summary paragraph - word for word",
  "objective": "Career objective if separate from summary",
  "skills": ["list all skills mentioned - every single one"],
  "skills_categorized": [
    {{
      "category": "Category name (e.g., Programming Languages)",
      "skills": ["skill1", "skill2", ...],
      "proficiency_levels": {{"skill": "level if mentioned"}}
    }}
  ],
  "education": [
    {{
      "degree": "Full degree name",
      "major": "Major/specialization if mentioned",
      "institution": "Full institution name",
      "location": "City, Country if mentioned",
      "start_date": "Start date in any format shown",
      "end_date": "End date or 'Present'",
      "graduation_year": 2024,
      "gpa": 3.8,
      "gpa_scale": 4.0,
      "honors": ["Any honors, dean's list, awards"],
      "relevant_coursework": ["Courses if listed"],
      "thesis": "Thesis title if mentioned",
      "activities": ["Student clubs, organizations"]
    }}
  ],
  "experience": [
    {{
      "title": "Full job title",
      "company": "Company name",
      "location": "City, Country",
      "employment_type": "Full-time/Part-time/Intern/Contract",
      "start_date": "Start date as shown",
      "end_date": "End date or 'Present'",
      "duration": "Duration string as shown",
      "is_current": true/false,
      "description": "Overall role description if given",
      "responsibilities": ["Every responsibility point - complete sentences"],
      "achievements": ["Every achievement - with numbers if shown"],
      "technologies": ["Every technology/tool mentioned"],
      "team_size": "Team size if mentioned",
      "metrics": ["Any metrics: 'Increased X by Y%'"]
    }}
  ],
  "projects": [
    {{
      "name": "Project name",
      "description": "Complete project description",
      "role": "Your role",
      "start_date": "Start",
      "end_date": "End",
      "technologies": ["All tech used"],
      "responsibilities": ["What you did"],
      "achievements": ["What you achieved"],
      "url": "Live URL if mentioned",
      "github": "GitHub repo if mentioned"
    }}
  ],
  "certifications": [
    {{
      "name": "Full certification name",
      "issuing_organization": "Issuing org",
      "issue_date": "When issued",
      "expiry_date": "When expires if shown",
      "credential_id": "ID if shown",
      "credential_url": "URL if shown"
    }}
  ],
  "awards": [
    {{
      "name": "Award name",
      "issuer": "Who gave it",
      "date": "When",
      "description": "Details if any"
    }}
  ],
  "languages": [
    {{
      "language": "Language name",
      "proficiency": "Native/Fluent/Professional/Basic",
      "reading": "level if specified",
      "writing": "level if specified",
      "speaking": "level if specified"
    }}
  ],
  "volunteer": [
    {{
      "organization": "Org name",
      "role": "Your role",
      "start_date": "Start",
      "end_date": "End",
      "description": "What you did",
      "achievements": ["Achievements"]
    }}
  ],
  "interests": ["All hobbies/interests listed"],
  "references": "References statement if shown"
}}

CRITICAL RULES:
1. Extract EVERY piece of information - do not summarize or skip anything
2. Keep original wording for descriptions, achievements, responsibilities
3. Preserve all dates, numbers, metrics exactly as shown
4. Include ALL skills mentioned anywhere in the CV
5. If a field is not found, use null or [] (empty array)
6. Keep original language (Vietnamese or English)
7. For arrays, include EVERY item, not just 2-3 examples
8. If multiple pages, extract from ALL pages

Return ONLY valid JSON, no markdown, no explanation.

JSON:"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert CV parser. Extract ALL information in complete detail. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temp for accuracy
            max_tokens=4000  # Increased for detailed output
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean markdown
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        
        # Parse JSON
        cv_data = json.loads(result_text.strip())
        
        # Convert to CVEnhanced model
        cv = convert_dict_to_cv_enhanced(cv_data, filename)
        
        print("✅ AI parsing successful (Enhanced)!")
        print(f"   Name: {cv.name}")
        print(f"   Email: {cv.contact.email}")
        print(f"   Skills: {len(cv.skills)}")
        print(f"   Experience: {len(cv.experience)}")
        print(f"   Projects: {len(cv.projects or [])}")
        print(f"   Certifications: {len(cv.certifications or [])}")
        
        return cv
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Response preview: {result_text[:500]}...")
        raise
    except Exception as e:
        print(f"❌ Parsing error: {e}")
        raise


def convert_dict_to_cv_enhanced(data: Dict, filename: str) -> CVEnhanced:
    """Convert parsed dict to CVEnhanced model"""
    
    # Contact info
    contact_data = data.get('contact', {})
    contact = ContactInfo(
        email=contact_data.get('email', ''),
        phone=contact_data.get('phone'),
        address=contact_data.get('address'),
        city=contact_data.get('city'),
        country=contact_data.get('country'),
        linkedin=contact_data.get('linkedin'),
        github=contact_data.get('github'),
        website=contact_data.get('website'),
        portfolio=contact_data.get('portfolio')
    )
    
    # Education
    education_list = []
    for edu in data.get('education', []):
        education_list.append(Education(
            degree=edu.get('degree', ''),
            major=edu.get('major'),
            institution=edu.get('institution', ''),
            location=edu.get('location'),
            start_date=edu.get('start_date'),
            end_date=edu.get('end_date'),
            graduation_year=edu.get('graduation_year'),
            gpa=edu.get('gpa'),
            gpa_scale=edu.get('gpa_scale', 4.0),
            honors=edu.get('honors') or [],
            relevant_coursework=edu.get('relevant_coursework') or [],
            thesis=edu.get('thesis'),
            activities=edu.get('activities') or []
        ))
    
    # Experience
    experience_list = []
    for exp in data.get('experience', []):
        experience_list.append(Experience(
            title=exp.get('title', ''),
            company=exp.get('company', ''),
            location=exp.get('location'),
            employment_type=exp.get('employment_type'),
            start_date=exp.get('start_date'),
            end_date=exp.get('end_date'),
            duration=exp.get('duration'),
            is_current=exp.get('is_current', False),
            description=exp.get('description'),
            responsibilities=exp.get('responsibilities') or [],
            achievements=exp.get('achievements') or [],
            technologies=exp.get('technologies') or [],
            team_size=exp.get('team_size'),
            metrics=exp.get('metrics', [])
        ))
    
    # Projects
    projects_list = []
    for proj in data.get('projects', []):
        projects_list.append(Project(
            name=proj.get('name', ''),
            description=proj.get('description', ''),
            role=proj.get('role'),
            start_date=proj.get('start_date'),
            end_date=proj.get('end_date'),
            duration=proj.get('duration'),
            technologies=proj.get('technologies') or [],
            responsibilities=proj.get('responsibilities') or [],
            achievements=proj.get('achievements') or [],
            url=proj.get('url'),
            github=proj.get('github'),
            demo_video=proj.get('demo_video')
        ))
    
    # Certifications
    certifications_list = []
    for cert in data.get('certifications', []):
        certifications_list.append(Certification(
            name=cert.get('name', ''),
            issuing_organization=cert.get('issuing_organization', ''),
            issue_date=cert.get('issue_date'),
            expiry_date=cert.get('expiry_date'),
            credential_id=cert.get('credential_id'),
            credential_url=cert.get('credential_url')
        ))
    
    # Languages
    languages_list = []
    for lang in data.get('languages', []):
        languages_list.append(Language(
            language=lang.get('language', ''),
            proficiency=lang.get('proficiency'),
            reading=lang.get('reading'),
            writing=lang.get('writing'),
            speaking=lang.get('speaking')
        ))
    
    # Skills categorized
    skills_cat_list = []
    for cat in data.get('skills_categorized', []):
        skills_cat_list.append(SkillCategory(
            category=cat.get('category', ''),
            skills=cat.get('skills', []),
            proficiency_levels=cat.get('proficiency_levels', {})
        ))
    
    # Create CV
    cv = CVEnhanced(
        name=data.get('name', 'Unknown'),
        title=data.get('title'),
        contact=contact,
        summary=data.get('summary'),
        objective=data.get('objective'),
        skills=data.get('skills', []),
        skills_categorized=skills_cat_list if skills_cat_list else None,
        education=education_list,
        experience=experience_list,
        projects=projects_list if projects_list else None,
        certifications=certifications_list if certifications_list else None,
        languages=languages_list if languages_list else None,
        interests=data.get('interests'),
        references=data.get('references'),
        parsed_date=datetime.now().isoformat(),
        original_filename=filename,
        cv_format="enhanced"
    )
    
    return cv


def parse_pdf_to_enhanced_json(pdf_path: str, output_json_path: Optional[str] = None) -> CVEnhanced:
    """
    Main function: Parse PDF CV to Enhanced JSON with ALL details
    """
    print("="*80)
    print("🚀 ENHANCED PDF CV PARSER - Extract ALL Details")
    print("="*80)
    
    # Step 1: Extract text
    cv_text = extract_text_from_pdf(pdf_path)
    
    # Step 2: Parse with AI (enhanced mode)
    import os
    filename = os.path.basename(pdf_path)
    cv = parse_cv_enhanced(cv_text, filename)
    
    # Step 3: Save to JSON
    if output_json_path:
        print(f"\n💾 Saving to: {output_json_path}")
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(cv.model_dump(), f, indent=2, ensure_ascii=False)
        print("✅ Enhanced JSON file saved!")
    
    # Step 4: Print summary
    print_cv_summary(cv)
    
    return cv


def print_cv_summary(cv: CVEnhanced):
    """Print detailed summary of parsed CV"""
    print("\n" + "="*80)
    print("📋 ENHANCED CV PARSING SUMMARY")
    print("="*80)
    
    print(f"\n👤 Personal Info:")
    print(f"   Name: {cv.name}")
    if cv.title:
        print(f"   Title: {cv.title}")
    print(f"   Email: {cv.contact.email}")
    if cv.contact.phone:
        print(f"   Phone: {cv.contact.phone}")
    if cv.contact.linkedin:
        print(f"   LinkedIn: {cv.contact.linkedin}")
    if cv.contact.github:
        print(f"   GitHub: {cv.contact.github}")
    
    if cv.summary:
        print(f"\n📝 Summary:")
        print(f"   {cv.summary[:200]}..." if len(cv.summary) > 200 else f"   {cv.summary}")
    
    print(f"\n🎯 Skills ({len(cv.skills)}):")
    for i, skill in enumerate(cv.skills[:15], 1):
        print(f"   {i}. {skill}")
    if len(cv.skills) > 15:
        print(f"   ... and {len(cv.skills) - 15} more")
    
    if cv.skills_categorized:
        print(f"\n🏷️  Skills by Category:")
        for cat in cv.skills_categorized:
            print(f"   {cat.category}: {len(cat.skills)} skills")
    
    print(f"\n🎓 Education ({len(cv.education)}):")
    for edu in cv.education:
        print(f"   • {edu.degree} - {edu.institution}")
        if edu.major:
            print(f"     Major: {edu.major}")
        if edu.gpa:
            print(f"     GPA: {edu.gpa}/{edu.gpa_scale}")
        if edu.start_date or edu.end_date:
            print(f"     Period: {edu.start_date or '?'} - {edu.end_date or '?'}")
    
    print(f"\n💼 Experience ({len(cv.experience)}):")
    for exp in cv.experience:
        print(f"   • {exp.title} at {exp.company}")
        if exp.location:
            print(f"     Location: {exp.location}")
        if exp.employment_type:
            print(f"     Type: {exp.employment_type}")
        print(f"     Period: {exp.start_date or '?'} - {exp.end_date or '?'}")
        print(f"     Responsibilities: {len(exp.responsibilities)} items")
        if exp.achievements:
            print(f"     Achievements: {len(exp.achievements)} items")
        if exp.technologies:
            print(f"     Tech: {', '.join(exp.technologies[:5])}")
    
    if cv.projects:
        print(f"\n🚀 Projects ({len(cv.projects)}):")
        for proj in cv.projects:
            print(f"   • {proj.name}")
            if proj.role:
                print(f"     Role: {proj.role}")
            if proj.technologies:
                print(f"     Tech: {', '.join(proj.technologies[:5])}")
    
    if cv.certifications:
        print(f"\n🏆 Certifications ({len(cv.certifications)}):")
        for cert in cv.certifications:
            print(f"   • {cert.name} - {cert.issuing_organization}")
            if cert.issue_date:
                print(f"     Issued: {cert.issue_date}")
    
    if cv.languages:
        print(f"\n🌐 Languages ({len(cv.languages)}):")
        for lang in cv.languages:
            proficiency = f" ({lang.proficiency})" if lang.proficiency else ""
            print(f"   • {lang.language}{proficiency}")
    
    print("\n" + "="*80)
    print("✅ ENHANCED PARSING COMPLETE!")
    print("="*80)


# Quick test
if __name__ == "__main__":
    pdf_path = "/Users/bill.nguyen.int/Desktop/KLTN/NguyenHongHiepCV.pdf"
    output_path = "/Users/bill.nguyen.int/Desktop/KLTN/NguyenHongHiepCV_enhanced.json"
    
    try:
        cv = parse_pdf_to_enhanced_json(pdf_path, output_path)
        
        print("\n" + "="*80)
        print("🎉 SUCCESS!")
        print("="*80)
        print(f"\n📁 Enhanced JSON saved to: {output_path}")
        print("\nThis JSON contains ALL details from your CV.")
        print("You can now use it to:")
        print("  1. Render back to CV (HTML/PDF)")
        print("  2. Store in database")
        print("  3. Send to matching API")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

