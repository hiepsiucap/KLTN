"""
Skill Ontology - Khung kỹ năng CNTT
===================================

Module này cung cấp:
1. Ontology kỹ năng với categories và hierarchy
2. Skill normalization (React.js = ReactJS = React)
3. Related skills mapping
4. Skill metadata (demand, salary, learning path)
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json


class SkillCategory(str, Enum):
    """Categories for IT skills"""
    PROGRAMMING_LANGUAGE = "Programming Language"
    FRONTEND_FRAMEWORK = "Frontend Framework"
    BACKEND_FRAMEWORK = "Backend Framework"
    DATABASE = "Database"
    DEVOPS = "DevOps"
    CLOUD = "Cloud"
    ARCHITECTURE = "Architecture"
    MESSAGE_QUEUE = "Message Queue"
    TESTING = "Testing"
    MOBILE = "Mobile"
    AI_ML = "AI/ML"
    SECURITY = "Security"
    VERSION_CONTROL = "Version Control"
    SOFT_SKILL = "Soft Skill"
    METHODOLOGY = "Methodology"
    OTHER = "Other"


class MarketDemand(str, Enum):
    """Market demand levels"""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NICHE = "niche"


@dataclass
class Skill:
    """Skill entity in ontology"""
    id: str
    name: str                           # Canonical name
    category: SkillCategory
    aliases: List[str]                  # Alternative names
    related_skills: List[str]           # Related/similar skills
    parent_skills: List[str]            # Prerequisite skills
    child_skills: List[str]             # Skills that build on this
    description: str
    learning_path: str
    best_practices: List[str]
    cv_tips: str
    market_demand: MarketDemand
    salary_range_vnd: str               # VND per month
    experience_level: str               # junior/mid/senior required
    keywords: List[str]                 # Keywords for matching


# ============================================================================
# SKILL ONTOLOGY DATABASE
# ============================================================================

SKILL_ONTOLOGY: Dict[str, Skill] = {}

def _register_skill(skill: Skill):
    """Register a skill in the ontology"""
    SKILL_ONTOLOGY[skill.id] = skill
    # Also register aliases for lookup
    for alias in skill.aliases:
        SKILL_ONTOLOGY[alias.lower()] = skill


# ===== PROGRAMMING LANGUAGES =====

_register_skill(Skill(
    id="python",
    name="Python",
    category=SkillCategory.PROGRAMMING_LANGUAGE,
    aliases=["python3", "py", "python 3", "python3.x"],
    related_skills=["django", "flask", "fastapi", "numpy", "pandas"],
    parent_skills=[],
    child_skills=["django", "flask", "fastapi", "data-science", "machine-learning"],
    description="Ngôn ngữ lập trình đa năng, phổ biến trong web, data science, AI/ML, automation.",
    learning_path="Python basics → OOP → Web framework (Django/Flask) → Testing → Async programming",
    best_practices=[
        "Sử dụng virtual environment (venv/conda)",
        "Follow PEP 8 style guide",
        "Viết unit tests với pytest",
        "Sử dụng type hints cho code rõ ràng"
    ],
    cv_tips="Liệt kê cụ thể frameworks (Django, FastAPI), không chỉ ghi 'Python'",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="15-50 triệu",
    experience_level="all",
    keywords=["python", "django", "flask", "fastapi", "pip", "pytest"]
))

_register_skill(Skill(
    id="javascript",
    name="JavaScript",
    category=SkillCategory.PROGRAMMING_LANGUAGE,
    aliases=["js", "es6", "es2015", "ecmascript", "vanilla js", "vanilla javascript"],
    related_skills=["typescript", "react", "vue", "angular", "nodejs"],
    parent_skills=[],
    child_skills=["typescript", "react", "vue", "angular", "nodejs"],
    description="Ngôn ngữ lập trình cho web, chạy cả frontend và backend (Node.js).",
    learning_path="JS basics → DOM → Framework (React/Vue) → Node.js → TypeScript",
    best_practices=[
        "Sử dụng TypeScript cho dự án lớn",
        "Dùng async/await thay callback",
        "Sử dụng ESLint và Prettier",
        "Viết code theo functional style"
    ],
    cv_tips="Ghi 'JavaScript (ES6+)' và frameworks cụ thể",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="12-45 triệu",
    experience_level="all",
    keywords=["javascript", "js", "es6", "node", "npm", "react", "vue"]
))

_register_skill(Skill(
    id="typescript",
    name="TypeScript",
    category=SkillCategory.PROGRAMMING_LANGUAGE,
    aliases=["ts", "type script"],
    related_skills=["javascript", "react", "angular", "nodejs", "nestjs"],
    parent_skills=["javascript"],
    child_skills=["nestjs", "angular"],
    description="JavaScript với static typing, giúp code an toàn và maintainable hơn.",
    learning_path="JavaScript proficiency → TS basics → Advanced types → Generics",
    best_practices=[
        "Sử dụng strict mode",
        "Define proper interfaces",
        "Avoid 'any' type",
        "Use utility types"
    ],
    cv_tips="TypeScript gần như bắt buộc cho Senior frontend roles",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="15-50 triệu",
    experience_level="mid",
    keywords=["typescript", "ts", "tsc", "types", "interfaces"]
))

_register_skill(Skill(
    id="go",
    name="Go",
    category=SkillCategory.PROGRAMMING_LANGUAGE,
    aliases=["golang", "go-lang", "go lang"],
    related_skills=["docker", "kubernetes", "microservices", "grpc"],
    parent_skills=[],
    child_skills=["microservices", "grpc"],
    description="Ngôn ngữ của Google, nổi bật về performance và concurrency.",
    learning_path="Go basics → Goroutines & Channels → Web (Gin/Echo) → gRPC → Cloud",
    best_practices=[
        "Sử dụng go modules",
        "Viết concurrent code với goroutines",
        "Follow effective go guidelines",
        "Sử dụng interfaces"
    ],
    cv_tips="Go developers rất hot, highlight microservices và cloud experience",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="20-60 triệu",
    experience_level="mid",
    keywords=["go", "golang", "goroutine", "channel", "gin", "echo"]
))

_register_skill(Skill(
    id="java",
    name="Java",
    category=SkillCategory.PROGRAMMING_LANGUAGE,
    aliases=["java8", "java11", "java17", "java21", "jdk", "jre"],
    related_skills=["spring-boot", "hibernate", "maven", "gradle"],
    parent_skills=[],
    child_skills=["spring-boot", "hibernate"],
    description="Ngôn ngữ enterprise, mạnh về OOP, phổ biến trong banking, fintech.",
    learning_path="Java Core → OOP → Spring Boot → JPA/Hibernate → Microservices",
    best_practices=[
        "Sử dụng Java 11+ (LTS)",
        "Follow SOLID principles",
        "Sử dụng Spring Boot",
        "Viết clean code"
    ],
    cv_tips="Ghi rõ version (Java 11/17) và Spring Boot experience",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="15-55 triệu",
    experience_level="all",
    keywords=["java", "spring", "maven", "gradle", "jvm", "hibernate"]
))

_register_skill(Skill(
    id="csharp",
    name="C#",
    category=SkillCategory.PROGRAMMING_LANGUAGE,
    aliases=["c-sharp", "c sharp", "csharp", ".net", "dotnet"],
    related_skills=["asp.net", "entity-framework", "azure"],
    parent_skills=[],
    child_skills=["asp.net", "unity"],
    description="Ngôn ngữ của Microsoft, dùng cho enterprise apps, game development (Unity).",
    learning_path="C# basics → OOP → ASP.NET Core → Entity Framework → Azure",
    best_practices=[
        "Sử dụng .NET 6+ (LTS)",
        "Follow C# coding conventions",
        "Use async/await properly",
        "Implement dependency injection"
    ],
    cv_tips="Ghi rõ .NET version và cloud experience (Azure)",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="15-50 triệu",
    experience_level="all",
    keywords=["c#", "csharp", ".net", "dotnet", "asp.net", "azure"]
))

_register_skill(Skill(
    id="rust",
    name="Rust",
    category=SkillCategory.PROGRAMMING_LANGUAGE,
    aliases=["rust-lang", "rustlang"],
    related_skills=["systems-programming", "webassembly"],
    parent_skills=["c", "cpp"],
    child_skills=["webassembly"],
    description="Systems programming language với memory safety, performance cao.",
    learning_path="Rust basics → Ownership & Borrowing → Async → Web frameworks",
    best_practices=[
        "Embrace the borrow checker",
        "Use cargo properly",
        "Write idiomatic Rust",
        "Leverage the type system"
    ],
    cv_tips="Rust developers rất khan hiếm và được trả lương cao",
    market_demand=MarketDemand.NICHE,
    salary_range_vnd="25-70 triệu",
    experience_level="mid",
    keywords=["rust", "cargo", "ownership", "borrowing"]
))

# ===== FRONTEND FRAMEWORKS =====

_register_skill(Skill(
    id="react",
    name="React",
    category=SkillCategory.FRONTEND_FRAMEWORK,
    aliases=["reactjs", "react.js", "react 18", "react js"],
    related_skills=["redux", "react-query", "nextjs", "typescript"],
    parent_skills=["javascript", "html", "css"],
    child_skills=["nextjs", "react-native"],
    description="Library JavaScript phổ biến nhất cho frontend, bởi Facebook/Meta.",
    learning_path="React basics → Hooks → State management → Next.js → Testing",
    best_practices=[
        "Sử dụng functional components và hooks",
        "Tránh prop drilling",
        "Optimize với React.memo, useMemo",
        "Viết tests với React Testing Library"
    ],
    cv_tips="Ghi 'React (Hooks, Redux)' thay vì chỉ 'React'",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="15-50 triệu",
    experience_level="all",
    keywords=["react", "jsx", "hooks", "redux", "component"]
))

_register_skill(Skill(
    id="vue",
    name="Vue.js",
    category=SkillCategory.FRONTEND_FRAMEWORK,
    aliases=["vuejs", "vue", "vue3", "vue 3", "vue.js 3"],
    related_skills=["vuex", "pinia", "nuxtjs", "typescript"],
    parent_skills=["javascript", "html", "css"],
    child_skills=["nuxtjs"],
    description="Framework JavaScript progressive, dễ học, phổ biến ở châu Á.",
    learning_path="Vue basics → Composition API → Pinia → Nuxt.js → Testing",
    best_practices=[
        "Sử dụng Composition API (Vue 3)",
        "Dùng Pinia thay Vuex",
        "Follow Vue style guide",
        "Sử dụng TypeScript"
    ],
    cv_tips="Ghi rõ Vue 2/3, Composition API hay Options API",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="12-40 triệu",
    experience_level="all",
    keywords=["vue", "vuex", "pinia", "composition api", "nuxt"]
))

_register_skill(Skill(
    id="angular",
    name="Angular",
    category=SkillCategory.FRONTEND_FRAMEWORK,
    aliases=["angular2", "angular 2+", "angularjs"],
    related_skills=["typescript", "rxjs", "ngrx"],
    parent_skills=["typescript", "html", "css"],
    child_skills=[],
    description="Framework đầy đủ của Google, mạnh về enterprise applications.",
    learning_path="TypeScript → Angular basics → RxJS → NgRx → Testing",
    best_practices=[
        "Follow Angular style guide",
        "Use lazy loading",
        "Implement proper state management",
        "Write tests với Jasmine/Karma"
    ],
    cv_tips="Angular phổ biến trong enterprise, ghi rõ version",
    market_demand=MarketDemand.MEDIUM,
    salary_range_vnd="15-45 triệu",
    experience_level="mid",
    keywords=["angular", "typescript", "rxjs", "ngrx", "module"]
))

_register_skill(Skill(
    id="nextjs",
    name="Next.js",
    category=SkillCategory.FRONTEND_FRAMEWORK,
    aliases=["next.js", "next js", "next 13", "next 14"],
    related_skills=["react", "typescript", "vercel"],
    parent_skills=["react"],
    child_skills=[],
    description="React framework với SSR, SSG, routing tích hợp.",
    learning_path="React proficiency → Next.js basics → App Router → API Routes → Deployment",
    best_practices=[
        "Sử dụng App Router (Next 13+)",
        "Optimize images với next/image",
        "Implement ISR for dynamic content",
        "Use Server Components"
    ],
    cv_tips="Next.js rất hot hiện nay, nên highlight trong CV",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="18-55 triệu",
    experience_level="mid",
    keywords=["next", "nextjs", "ssr", "ssg", "vercel", "app router"]
))

_register_skill(Skill(
    id="tailwindcss",
    name="Tailwind CSS",
    category=SkillCategory.FRONTEND_FRAMEWORK,
    aliases=["tailwind", "tailwind css"],
    related_skills=["css", "html", "react", "vue"],
    parent_skills=["css", "html"],
    child_skills=[],
    description="Utility-first CSS framework, rất phổ biến hiện nay.",
    learning_path="CSS basics → Tailwind classes → Responsive design → Custom config",
    best_practices=[
        "Sử dụng @apply cho reusable styles",
        "Custom config cho design system",
        "Use JIT mode",
        "Combine với component libraries"
    ],
    cv_tips="Tailwind được yêu cầu nhiều, nên có trong tech stack",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm Frontend role",
    experience_level="all",
    keywords=["tailwind", "utility-first", "css", "responsive"]
))

# ===== BACKEND FRAMEWORKS =====

_register_skill(Skill(
    id="nodejs",
    name="Node.js",
    category=SkillCategory.BACKEND_FRAMEWORK,
    aliases=["node", "node.js", "nodejs", "node js"],
    related_skills=["express", "nestjs", "typescript", "mongodb"],
    parent_skills=["javascript"],
    child_skills=["express", "nestjs", "fastify"],
    description="JavaScript runtime cho backend, non-blocking I/O, real-time apps.",
    learning_path="Node basics → Express/NestJS → Database → Authentication → Testing",
    best_practices=[
        "Sử dụng TypeScript",
        "Implement error handling middleware",
        "Sử dụng environment variables",
        "Follow 12-factor app"
    ],
    cv_tips="Ghi cụ thể framework (Express, NestJS) và databases",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="15-45 triệu",
    experience_level="all",
    keywords=["node", "npm", "express", "nestjs", "fastify"]
))

_register_skill(Skill(
    id="express",
    name="Express.js",
    category=SkillCategory.BACKEND_FRAMEWORK,
    aliases=["expressjs", "express.js", "express js"],
    related_skills=["nodejs", "mongodb", "postgresql"],
    parent_skills=["nodejs"],
    child_skills=[],
    description="Minimal Node.js web framework, phổ biến nhất cho Node backend.",
    learning_path="Node.js basics → Express routing → Middleware → Authentication",
    best_practices=[
        "Use middleware properly",
        "Implement error handling",
        "Structure project properly",
        "Use helmet for security"
    ],
    cv_tips="Express là baseline, nên có thêm NestJS để nổi bật",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm Node.js role",
    experience_level="all",
    keywords=["express", "middleware", "routing", "rest api"]
))

_register_skill(Skill(
    id="nestjs",
    name="NestJS",
    category=SkillCategory.BACKEND_FRAMEWORK,
    aliases=["nest.js", "nest js", "nest"],
    related_skills=["typescript", "nodejs", "graphql"],
    parent_skills=["nodejs", "typescript"],
    child_skills=[],
    description="Enterprise Node.js framework với TypeScript, inspired by Angular.",
    learning_path="TypeScript → NestJS basics → Modules → Guards/Pipes → Testing",
    best_practices=[
        "Follow modular architecture",
        "Use dependency injection",
        "Implement proper validation",
        "Write comprehensive tests"
    ],
    cv_tips="NestJS được ưa chuộng hơn Express cho Senior roles",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="20-50 triệu",
    experience_level="mid",
    keywords=["nestjs", "decorator", "module", "controller", "service"]
))

_register_skill(Skill(
    id="django",
    name="Django",
    category=SkillCategory.BACKEND_FRAMEWORK,
    aliases=["django-rest-framework", "drf", "django rest"],
    related_skills=["python", "postgresql", "celery", "redis"],
    parent_skills=["python"],
    child_skills=["django-rest-framework"],
    description="Python web framework 'batteries-included', rapid development và security.",
    learning_path="Django basics → Models & ORM → REST API (DRF) → Celery → Deploy",
    best_practices=[
        "Sử dụng Django REST Framework",
        "Implement JWT authentication",
        "Sử dụng Celery cho async",
        "Follow security best practices"
    ],
    cv_tips="Highlight DRF, Celery experience",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="15-45 triệu",
    experience_level="all",
    keywords=["django", "drf", "orm", "celery", "admin"]
))

_register_skill(Skill(
    id="fastapi",
    name="FastAPI",
    category=SkillCategory.BACKEND_FRAMEWORK,
    aliases=["fast-api", "fast api"],
    related_skills=["python", "pydantic", "async", "openapi"],
    parent_skills=["python"],
    child_skills=[],
    description="Modern Python framework, async, auto-docs, type hints.",
    learning_path="Python async → FastAPI basics → Pydantic → Background tasks",
    best_practices=[
        "Use Pydantic models",
        "Implement dependency injection",
        "Leverage async/await",
        "Auto-generate OpenAPI docs"
    ],
    cv_tips="FastAPI đang lên, rất hot cho microservices",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="18-50 triệu",
    experience_level="mid",
    keywords=["fastapi", "pydantic", "async", "openapi", "uvicorn"]
))

_register_skill(Skill(
    id="spring-boot",
    name="Spring Boot",
    category=SkillCategory.BACKEND_FRAMEWORK,
    aliases=["springboot", "spring-boot", "spring boot", "spring"],
    related_skills=["java", "hibernate", "maven", "microservices"],
    parent_skills=["java"],
    child_skills=["spring-cloud"],
    description="Java framework phổ biến nhất cho enterprise backend.",
    learning_path="Java Core → Spring basics → Spring Boot → Security → Cloud",
    best_practices=[
        "Use Spring Initializr",
        "Implement proper layering",
        "Use Spring Security",
        "Follow 12-factor app"
    ],
    cv_tips="Spring Boot gần như bắt buộc cho Java backend roles",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="18-55 triệu",
    experience_level="all",
    keywords=["spring", "boot", "bean", "autowired", "jpa"]
))

# ===== DATABASES =====

_register_skill(Skill(
    id="postgresql",
    name="PostgreSQL",
    category=SkillCategory.DATABASE,
    aliases=["postgres", "psql", "pg", "postgre"],
    related_skills=["sql", "database-design", "indexing"],
    parent_skills=["sql"],
    child_skills=[],
    description="Open-source relational database mạnh nhất, hỗ trợ JSON, full-text search.",
    learning_path="SQL basics → Indexing → Query optimization → Replication → Tuning",
    best_practices=[
        "Proper indexing strategy",
        "Use EXPLAIN ANALYZE",
        "Connection pooling (PgBouncer)",
        "Regular VACUUM"
    ],
    cv_tips="Ghi cụ thể: query optimization, millions of records, replication",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="Đi kèm Backend role",
    experience_level="all",
    keywords=["postgresql", "postgres", "sql", "query", "index"]
))

_register_skill(Skill(
    id="mysql",
    name="MySQL",
    category=SkillCategory.DATABASE,
    aliases=["my-sql", "mariadb"],
    related_skills=["sql", "database-design"],
    parent_skills=["sql"],
    child_skills=[],
    description="Relational database phổ biến, dễ sử dụng, widespread adoption.",
    learning_path="SQL basics → Indexing → Optimization → Replication",
    best_practices=[
        "Use InnoDB engine",
        "Proper indexing",
        "Optimize slow queries",
        "Regular backups"
    ],
    cv_tips="MySQL phổ biến nhưng PostgreSQL đang được ưa chuộng hơn",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm Backend role",
    experience_level="all",
    keywords=["mysql", "sql", "mariadb", "innodb"]
))

_register_skill(Skill(
    id="mongodb",
    name="MongoDB",
    category=SkillCategory.DATABASE,
    aliases=["mongo", "nosql", "document db"],
    related_skills=["mongoose", "nosql", "aggregation"],
    parent_skills=[],
    child_skills=[],
    description="Document database phổ biến nhất, linh hoạt, rapid development.",
    learning_path="CRUD → Aggregation → Indexing → Replication → Sharding",
    best_practices=[
        "Design schema for queries",
        "Proper indexing",
        "Avoid large documents",
        "Use aggregation pipeline"
    ],
    cv_tips="Highlight large datasets, aggregation pipeline experience",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm Backend role",
    experience_level="all",
    keywords=["mongodb", "mongo", "document", "nosql", "aggregation"]
))

_register_skill(Skill(
    id="redis",
    name="Redis",
    category=SkillCategory.DATABASE,
    aliases=["redis cache", "in-memory", "redis db"],
    related_skills=["caching", "pub-sub", "session"],
    parent_skills=[],
    child_skills=[],
    description="In-memory data store cho caching, sessions, real-time.",
    learning_path="Data structures → Caching patterns → Pub/Sub → Clustering",
    best_practices=[
        "Set appropriate TTL",
        "Use data structures properly",
        "Cache invalidation strategy",
        "Monitor memory"
    ],
    cv_tips="Redis thường yêu cầu cho Senior Backend roles",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm Backend role",
    experience_level="mid",
    keywords=["redis", "cache", "memory", "pub/sub", "session"]
))

_register_skill(Skill(
    id="elasticsearch",
    name="Elasticsearch",
    category=SkillCategory.DATABASE,
    aliases=["elastic", "es", "elk", "opensearch"],
    related_skills=["full-text-search", "logging", "kibana"],
    parent_skills=[],
    child_skills=[],
    description="Search và analytics engine, dùng cho full-text search, logging (ELK).",
    learning_path="Basics → Queries → Mappings → Aggregations → Clustering",
    best_practices=[
        "Proper index mapping",
        "Use bulk operations",
        "Optimize queries",
        "Monitor cluster health"
    ],
    cv_tips="Elasticsearch valuable cho search-heavy và logging systems",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm Senior Backend/DevOps role",
    experience_level="mid",
    keywords=["elasticsearch", "elastic", "search", "kibana", "logstash"]
))

# ===== DEVOPS =====

_register_skill(Skill(
    id="docker",
    name="Docker",
    category=SkillCategory.DEVOPS,
    aliases=["docker-compose", "containerization", "container"],
    related_skills=["kubernetes", "ci-cd", "linux"],
    parent_skills=["linux"],
    child_skills=["kubernetes", "docker-compose"],
    description="Container platform, đóng gói và deploy applications nhất quán.",
    learning_path="Docker basics → Dockerfile → Docker Compose → Orchestration (K8s)",
    best_practices=[
        "Multi-stage builds",
        "Minimize image size",
        "Don't run as root",
        "Use .dockerignore"
    ],
    cv_tips="Docker gần như bắt buộc cho Senior roles",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="Đi kèm Backend/DevOps role",
    experience_level="mid",
    keywords=["docker", "container", "dockerfile", "compose", "image"]
))

_register_skill(Skill(
    id="kubernetes",
    name="Kubernetes",
    category=SkillCategory.DEVOPS,
    aliases=["k8s", "kube", "k8", "kubernetes cluster"],
    related_skills=["docker", "helm", "aws-eks", "gke"],
    parent_skills=["docker", "linux"],
    child_skills=["helm", "istio"],
    description="Container orchestration platform, industry standard cho scaling.",
    learning_path="K8s concepts → Deployments & Services → Helm → Monitoring → GitOps",
    best_practices=[
        "Use Helm",
        "Implement health checks",
        "Set resource limits",
        "Follow GitOps"
    ],
    cv_tips="K8s rất valuable, có CKA/CKAD certification càng tốt",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="25-70 triệu (DevOps/SRE)",
    experience_level="mid",
    keywords=["kubernetes", "k8s", "pod", "deployment", "service", "helm"]
))

_register_skill(Skill(
    id="ci-cd",
    name="CI/CD",
    category=SkillCategory.DEVOPS,
    aliases=["cicd", "continuous integration", "continuous deployment", "pipeline"],
    related_skills=["github-actions", "jenkins", "gitlab-ci"],
    parent_skills=["git"],
    child_skills=["github-actions", "jenkins"],
    description="Continuous Integration & Deployment, automation cho build và deploy.",
    learning_path="Git → CI basics → CD basics → Advanced pipelines → GitOps",
    best_practices=[
        "Automate everything",
        "Fast feedback loops",
        "Implement testing stages",
        "Use infrastructure as code"
    ],
    cv_tips="CI/CD experience quan trọng, ghi cụ thể tools đã dùng",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="Đi kèm DevOps role",
    experience_level="mid",
    keywords=["ci/cd", "pipeline", "jenkins", "github actions", "gitlab ci"]
))

_register_skill(Skill(
    id="github-actions",
    name="GitHub Actions",
    category=SkillCategory.DEVOPS,
    aliases=["gh actions", "github action"],
    related_skills=["ci-cd", "git", "docker"],
    parent_skills=["git", "ci-cd"],
    child_skills=[],
    description="CI/CD platform của GitHub, dễ sử dụng và free cho open source.",
    learning_path="Workflows → Jobs & Steps → Secrets → Matrix builds → Reusable workflows",
    best_practices=[
        "Use reusable workflows",
        "Cache dependencies",
        "Use matrix for multiple versions",
        "Implement proper secrets management"
    ],
    cv_tips="GitHub Actions phổ biến, nên có kinh nghiệm",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm DevOps role",
    experience_level="all",
    keywords=["github actions", "workflow", "yaml", "automation"]
))

_register_skill(Skill(
    id="terraform",
    name="Terraform",
    category=SkillCategory.DEVOPS,
    aliases=["tf", "terraform cloud", "hcl"],
    related_skills=["aws", "gcp", "azure", "infrastructure-as-code"],
    parent_skills=["cloud"],
    child_skills=[],
    description="Infrastructure as Code tool, multi-cloud support.",
    learning_path="IaC concepts → Terraform basics → Modules → State management → Multi-env",
    best_practices=[
        "Use modules",
        "Remote state with locking",
        "Use workspaces/environments",
        "Implement proper testing"
    ],
    cv_tips="Terraform rất valuable cho DevOps/Cloud roles",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="25-60 triệu (DevOps)",
    experience_level="mid",
    keywords=["terraform", "hcl", "infrastructure", "iac", "module"]
))

# ===== CLOUD =====

_register_skill(Skill(
    id="aws",
    name="AWS",
    category=SkillCategory.CLOUD,
    aliases=["amazon web services", "aws cloud", "amazon aws"],
    related_skills=["ec2", "s3", "rds", "lambda", "eks"],
    parent_skills=[],
    child_skills=["ec2", "s3", "lambda", "eks"],
    description="Cloud platform lớn nhất thế giới, 200+ services.",
    learning_path="Core (EC2, S3, RDS) → Networking (VPC) → Serverless → Containers → IaC",
    best_practices=[
        "Follow Well-Architected Framework",
        "IAM least privilege",
        "Use IaC (Terraform/CDK)",
        "Monitor với CloudWatch"
    ],
    cv_tips="AWS certifications (SAA, SAP) rất valuable",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="20-70 triệu",
    experience_level="all",
    keywords=["aws", "ec2", "s3", "lambda", "cloudformation", "iam"]
))

_register_skill(Skill(
    id="gcp",
    name="Google Cloud Platform",
    category=SkillCategory.CLOUD,
    aliases=["gcp", "google cloud", "gcloud"],
    related_skills=["gke", "bigquery", "cloud-run"],
    parent_skills=[],
    child_skills=["gke", "bigquery"],
    description="Cloud platform của Google, mạnh về data và ML.",
    learning_path="Core services → GKE → BigQuery → ML services → IaC",
    best_practices=[
        "Use managed services",
        "Implement proper IAM",
        "Leverage BigQuery",
        "Use Cloud Run for serverless"
    ],
    cv_tips="GCP phổ biến ở các tech companies lớn",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="20-65 triệu",
    experience_level="mid",
    keywords=["gcp", "gke", "bigquery", "cloud run", "firebase"]
))

_register_skill(Skill(
    id="azure",
    name="Microsoft Azure",
    category=SkillCategory.CLOUD,
    aliases=["azure cloud", "ms azure"],
    related_skills=["azure-devops", "aks", "azure-functions"],
    parent_skills=[],
    child_skills=["aks", "azure-functions"],
    description="Cloud platform của Microsoft, mạnh trong enterprise.",
    learning_path="Core services → AKS → Azure DevOps → IaC → Security",
    best_practices=[
        "Use Azure AD properly",
        "Implement proper networking",
        "Use managed services",
        "Integrate với Azure DevOps"
    ],
    cv_tips="Azure phổ biến trong enterprise và .NET stack",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="20-60 triệu",
    experience_level="mid",
    keywords=["azure", "aks", "azure devops", "azure functions"]
))

# ===== ARCHITECTURE & PATTERNS =====

_register_skill(Skill(
    id="microservices",
    name="Microservices",
    category=SkillCategory.ARCHITECTURE,
    aliases=["microservice architecture", "distributed systems", "micro-services"],
    related_skills=["docker", "kubernetes", "api-gateway", "kafka"],
    parent_skills=["system-design"],
    child_skills=[],
    description="Kiến trúc chia app thành services nhỏ, độc lập, dễ scale.",
    learning_path="Monolith → Service decomposition → Communication → Observability",
    best_practices=[
        "Design for failure",
        "Distributed tracing",
        "Event-driven where appropriate",
        "Avoid distributed monolith"
    ],
    cv_tips="Highlight số services đã design/maintain, patterns đã dùng",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="25-70 triệu (Senior/Architect)",
    experience_level="senior",
    keywords=["microservices", "distributed", "service mesh", "api gateway"]
))

_register_skill(Skill(
    id="rest-api",
    name="REST API",
    category=SkillCategory.ARCHITECTURE,
    aliases=["restful", "rest", "restful api", "api design"],
    related_skills=["http", "json", "openapi", "swagger"],
    parent_skills=[],
    child_skills=["graphql"],
    description="Architectural style cho web APIs, sử dụng HTTP methods.",
    learning_path="HTTP basics → REST principles → API design → Versioning → Documentation",
    best_practices=[
        "Follow REST conventions",
        "Proper HTTP status codes",
        "Version APIs",
        "Document với OpenAPI/Swagger"
    ],
    cv_tips="REST API là basic requirement, nên có thêm GraphQL",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="Đi kèm Backend role",
    experience_level="all",
    keywords=["rest", "api", "http", "json", "swagger", "openapi"]
))

_register_skill(Skill(
    id="graphql",
    name="GraphQL",
    category=SkillCategory.ARCHITECTURE,
    aliases=["graph-ql", "gql"],
    related_skills=["apollo", "rest-api", "nodejs"],
    parent_skills=["rest-api"],
    child_skills=[],
    description="Query language cho APIs, client định nghĩa data cần lấy.",
    learning_path="GraphQL basics → Schemas → Resolvers → Apollo → Best practices",
    best_practices=[
        "Design schema carefully",
        "Implement proper caching",
        "Use DataLoader for N+1",
        "Implement proper error handling"
    ],
    cv_tips="GraphQL experience làm CV nổi bật, đặc biệt với Apollo",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="Đi kèm Backend role",
    experience_level="mid",
    keywords=["graphql", "apollo", "query", "mutation", "schema"]
))

_register_skill(Skill(
    id="system-design",
    name="System Design",
    category=SkillCategory.ARCHITECTURE,
    aliases=["system architecture", "software architecture", "hld"],
    related_skills=["microservices", "distributed-systems", "scalability"],
    parent_skills=[],
    child_skills=["microservices"],
    description="Kỹ năng thiết kế hệ thống lớn, scalable, reliable.",
    learning_path="Fundamentals → Common patterns → Case studies → Trade-offs analysis",
    best_practices=[
        "Understand requirements first",
        "Consider scalability from start",
        "Design for failure",
        "Document decisions (ADRs)"
    ],
    cv_tips="System design là key cho Senior+ roles, highlight các hệ thống đã design",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="30-100+ triệu (Senior/Architect)",
    experience_level="senior",
    keywords=["system design", "architecture", "scalability", "reliability"]
))

# ===== MESSAGE QUEUES =====

_register_skill(Skill(
    id="kafka",
    name="Apache Kafka",
    category=SkillCategory.MESSAGE_QUEUE,
    aliases=["kafka", "event streaming", "confluent"],
    related_skills=["event-driven", "microservices", "stream-processing"],
    parent_skills=["microservices"],
    child_skills=[],
    description="Distributed event streaming platform cho real-time data pipelines.",
    learning_path="Kafka basics → Producers/Consumers → Partitioning → Streams → Connect",
    best_practices=[
        "Proper partitioning",
        "Idempotent consumers",
        "Schema registry",
        "Monitor consumer lag"
    ],
    cv_tips="Kafka experience rất valuable cho big tech companies",
    market_demand=MarketDemand.HIGH,
    salary_range_vnd="25-60 triệu (Senior)",
    experience_level="mid",
    keywords=["kafka", "topic", "partition", "consumer", "producer"]
))

_register_skill(Skill(
    id="rabbitmq",
    name="RabbitMQ",
    category=SkillCategory.MESSAGE_QUEUE,
    aliases=["rabbit", "amqp"],
    related_skills=["message-queue", "async", "microservices"],
    parent_skills=[],
    child_skills=[],
    description="Message broker phổ biến, dễ setup và sử dụng.",
    learning_path="Basics → Exchanges → Queues → Routing → Clustering",
    best_practices=[
        "Use proper exchange types",
        "Implement dead letter queues",
        "Handle message acknowledgments",
        "Monitor queue depths"
    ],
    cv_tips="RabbitMQ là entry point tốt cho message queues",
    market_demand=MarketDemand.MEDIUM,
    salary_range_vnd="Đi kèm Backend role",
    experience_level="mid",
    keywords=["rabbitmq", "queue", "exchange", "amqp", "message"]
))

# ===== TESTING =====

_register_skill(Skill(
    id="unit-testing",
    name="Unit Testing",
    category=SkillCategory.TESTING,
    aliases=["unit test", "testing", "tdd"],
    related_skills=["jest", "pytest", "junit", "mocha"],
    parent_skills=[],
    child_skills=["integration-testing"],
    description="Testing individual units of code để đảm bảo correctness.",
    learning_path="Testing fundamentals → Mocking → TDD → Coverage → Best practices",
    best_practices=[
        "Write tests first (TDD)",
        "Follow AAA pattern",
        "Mock external dependencies",
        "Aim for high coverage"
    ],
    cv_tips="Testing skills quan trọng, ghi rõ tools và coverage đạt được",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="Đi kèm mọi dev role",
    experience_level="all",
    keywords=["unit test", "testing", "tdd", "mock", "coverage"]
))

# ===== VERSION CONTROL =====

_register_skill(Skill(
    id="git",
    name="Git",
    category=SkillCategory.VERSION_CONTROL,
    aliases=["github", "gitlab", "bitbucket", "version control"],
    related_skills=["github", "gitlab", "ci-cd"],
    parent_skills=[],
    child_skills=["github-actions", "gitlab-ci"],
    description="Version control system phổ biến nhất, bắt buộc cho mọi developer.",
    learning_path="Basic commands → Branching → Merging → Rebasing → Git Flow",
    best_practices=[
        "Meaningful commit messages",
        "Use feature branches",
        "Regular small commits",
        "Code review process"
    ],
    cv_tips="Git là bắt buộc, không cần list riêng trừ khi junior",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="Bắt buộc",
    experience_level="all",
    keywords=["git", "github", "gitlab", "commit", "branch", "merge"]
))

# ===== SOFT SKILLS =====

_register_skill(Skill(
    id="agile",
    name="Agile/Scrum",
    category=SkillCategory.METHODOLOGY,
    aliases=["scrum", "agile methodology", "kanban", "sprint"],
    related_skills=["jira", "confluence", "project-management"],
    parent_skills=[],
    child_skills=[],
    description="Phương pháp phát triển linh hoạt, Scrum là framework phổ biến nhất.",
    learning_path="Agile principles → Scrum → Tools (JIRA) → Estimation → Retrospectives",
    best_practices=[
        "Active ceremony participation",
        "Proper estimation",
        "Regular retrospectives",
        "Focus on value delivery"
    ],
    cv_tips="Agile/Scrum thường được assume, ghi nếu có certification",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="Required",
    experience_level="all",
    keywords=["agile", "scrum", "sprint", "kanban", "standup"]
))

# ===== AI/ML =====

_register_skill(Skill(
    id="machine-learning",
    name="Machine Learning",
    category=SkillCategory.AI_ML,
    aliases=["ml", "ai", "artificial intelligence"],
    related_skills=["python", "tensorflow", "pytorch", "scikit-learn"],
    parent_skills=["python", "statistics"],
    child_skills=["deep-learning", "nlp"],
    description="Xây dựng models học từ data để predictions/decisions.",
    learning_path="Math foundations → ML algorithms → Framework (sklearn) → Deep Learning",
    best_practices=[
        "Understand the math",
        "Proper data preprocessing",
        "Cross-validation",
        "Model evaluation"
    ],
    cv_tips="ML roles đòi hỏi projects cụ thể, papers published nếu có",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="25-80 triệu",
    experience_level="mid",
    keywords=["machine learning", "ml", "ai", "model", "training"]
))

_register_skill(Skill(
    id="llm",
    name="LLM/GenAI",
    category=SkillCategory.AI_ML,
    aliases=["large language models", "generative ai", "chatgpt", "gpt"],
    related_skills=["openai", "langchain", "rag", "prompt-engineering"],
    parent_skills=["machine-learning"],
    child_skills=[],
    description="Làm việc với Large Language Models như GPT, Claude, Llama.",
    learning_path="LLM basics → Prompt engineering → RAG → Fine-tuning → Agents",
    best_practices=[
        "Effective prompt engineering",
        "Implement RAG for accuracy",
        "Handle hallucinations",
        "Cost optimization"
    ],
    cv_tips="LLM/GenAI experience rất hot hiện nay, highlight các projects",
    market_demand=MarketDemand.VERY_HIGH,
    salary_range_vnd="30-100 triệu",
    experience_level="mid",
    keywords=["llm", "gpt", "openai", "langchain", "rag", "prompt"]
))


# ============================================================================
# ONTOLOGY QUERY FUNCTIONS
# ============================================================================

def get_skill(skill_name: str) -> Optional[Skill]:
    """Get skill by name or alias"""
    normalized = skill_name.lower().strip()
    
    # Direct lookup
    if normalized in SKILL_ONTOLOGY:
        return SKILL_ONTOLOGY[normalized]
    
    # Search in aliases
    for skill in SKILL_ONTOLOGY.values():
        if isinstance(skill, Skill):
            if normalized == skill.name.lower():
                return skill
            if normalized in [a.lower() for a in skill.aliases]:
                return skill
            if normalized in [k.lower() for k in skill.keywords]:
                return skill
    
    return None


def normalize_skill_name(skill_name: str) -> str:
    """Normalize skill name to canonical form"""
    skill = get_skill(skill_name)
    if skill:
        return skill.name
    return skill_name  # Return original if not found


def get_related_skills(skill_name: str) -> List[str]:
    """Get related skills for a given skill"""
    skill = get_skill(skill_name)
    if skill:
        return skill.related_skills
    return []


def get_skills_by_category(category: SkillCategory) -> List[Skill]:
    """Get all skills in a category"""
    skills = []
    seen_ids = set()
    
    for skill in SKILL_ONTOLOGY.values():
        if isinstance(skill, Skill) and skill.id not in seen_ids:
            if skill.category == category:
                skills.append(skill)
                seen_ids.add(skill.id)
    
    return skills


def get_skill_categories() -> List[str]:
    """Get all skill categories"""
    return [cat.value for cat in SkillCategory]


def get_all_skills() -> List[Skill]:
    """Get all unique skills"""
    skills = []
    seen_ids = set()
    
    for skill in SKILL_ONTOLOGY.values():
        if isinstance(skill, Skill) and skill.id not in seen_ids:
            skills.append(skill)
            seen_ids.add(skill.id)
    
    return skills


def search_skills(query: str) -> List[Skill]:
    """Search skills by query"""
    query = query.lower()
    results = []
    seen_ids = set()
    
    for skill in SKILL_ONTOLOGY.values():
        if isinstance(skill, Skill) and skill.id not in seen_ids:
            # Check name, aliases, keywords
            if query in skill.name.lower():
                results.append(skill)
                seen_ids.add(skill.id)
            elif any(query in alias.lower() for alias in skill.aliases):
                results.append(skill)
                seen_ids.add(skill.id)
            elif any(query in kw.lower() for kw in skill.keywords):
                results.append(skill)
                seen_ids.add(skill.id)
    
    return results


# ============================================================================
# EXPORT
# ============================================================================

def export_ontology_to_json() -> str:
    """Export ontology to JSON format"""
    skills = get_all_skills()
    
    data = {
        "categories": get_skill_categories(),
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category.value,
                "aliases": s.aliases,
                "related_skills": s.related_skills,
                "parent_skills": s.parent_skills,
                "child_skills": s.child_skills,
                "description": s.description,
                "learning_path": s.learning_path,
                "best_practices": s.best_practices,
                "cv_tips": s.cv_tips,
                "market_demand": s.market_demand.value,
                "salary_range_vnd": s.salary_range_vnd,
                "experience_level": s.experience_level,
                "keywords": s.keywords
            }
            for s in skills
        ]
    }
    
    return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("SKILL ONTOLOGY TEST")
    print("="*60)
    
    # Test get skill
    print("\n1. Get skill 'react':")
    skill = get_skill("react")
    if skill:
        print(f"   Name: {skill.name}")
        print(f"   Category: {skill.category.value}")
        print(f"   Related: {skill.related_skills}")
    
    # Test normalize
    print("\n2. Normalize skill names:")
    test_names = ["reactjs", "React.js", "react 18", "k8s", "golang", "psql"]
    for name in test_names:
        print(f"   '{name}' → '{normalize_skill_name(name)}'")
    
    # Test category
    print("\n3. Backend frameworks:")
    for s in get_skills_by_category(SkillCategory.BACKEND_FRAMEWORK):
        print(f"   - {s.name}")
    
    # Test search
    print("\n4. Search 'python':")
    for s in search_skills("python"):
        print(f"   - {s.name} ({s.category.value})")
    
    # Stats
    print(f"\n5. Total skills in ontology: {len(get_all_skills())}")
    print(f"   Categories: {len(get_skill_categories())}")

