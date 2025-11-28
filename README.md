# LGIR CV Matching API 🚀

API chấm điểm CV matching với Job Description sử dụng phương pháp LGIR (Learning from Generative Interactions for Recruitment).

## 📋 Mục lục

- [Tính năng](#tính-năng)
- [Cài đặt](#cài-đặt)
- [Cấu hình](#cấu-hình)
- [Chạy ứng dụng](#chạy-ứng-dụng)
- [API Documentation](#api-documentation)
- [Ví dụ sử dụng](#ví-dụ-sử-dụng)
- [Deploy](#deploy)
- [Công nghệ](#công-nghệ)

## ✨ Tính năng

### 1. Parse CV (PDF → JSON)
- Upload PDF CV và tự động parse thành JSON format
- Trích xuất thông tin: tên, email, skills, kinh nghiệm, học vấn, chứng chỉ
- Hỗ trợ cả tiếng Việt và tiếng Anh

### 2. Chấm điểm CV Matching
- Đánh giá độ phù hợp CV với nhiều Job Description
- Scoring theo 4 tiêu chí:
  - Overall Score (0-100)
  - Skills Match Score
  - Experience Match Score
  - Education Match Score
- Phân tích điểm mạnh, điểm yếu, khoảng cách kỹ năng
- Đưa ra gợi ý cải thiện CV

### 3. LGIR Features
- **Resume Completion**: Tự động bổ sung thông tin CV
- **Interactive Learning**: Học từ lịch sử tương tác của user
- **Quality Detection**: Phát hiện chất lượng CV
- **GAN Refinement**: Cải thiện CV chất lượng thấp
- **Deterministic Scoring**: Điểm số ổn định (temperature=0.0)

## 🚀 Cài đặt

### Yêu cầu
- Python 3.8+
- OpenAI API Key

### Bước 1: Clone repository

```bash
git clone <your-repo-url>
cd KLTN
```

### Bước 2: Tạo virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# hoặc
venv\Scripts\activate  # Windows
```

### Bước 3: Cài đặt dependencies

```bash
pip install -r requirements_production.txt
```

## ⚙️ Cấu hình

### Tạo file .env

Copy file mẫu và điền thông tin:

```bash
cp config.env.example .env
```

Mở file `.env` và cập nhật:

```env
# OpenAI API Key (Required)
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Server Port (Default: 8000)
PORT=8000
```

**⚠️ QUAN TRỌNG**: 
- File `.env` chứa thông tin nhạy cảm, KHÔNG được commit lên Git
- File `.env` đã được thêm vào `.gitignore`
- Chỉ commit file `config.env.example` (file mẫu)

### Lấy OpenAI API Key

1. Truy cập https://platform.openai.com/api-keys
2. Tạo API key mới
3. Copy và paste vào file `.env`

## 🏃 Chạy ứng dụng

### Chạy local

```bash
python server_production.py
```

Server sẽ chạy tại: `http://localhost:8000`

### Chạy với Docker

```bash
# Build image
docker build -t lgir-cv-api .

# Run container
docker run -d \
  --name lgir-api \
  -p 8000:8000 \
  --env-file .env \
  lgir-cv-api
```

### Chạy với Docker Compose

```bash
docker-compose up -d
```

## 📚 API Documentation

Sau khi chạy server, truy cập:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints chính:

#### 1. Parse PDF CV
```
POST /parse/pdf
```
Upload PDF file → Returns JSON CV data

**Example:**
```bash
curl -X POST http://localhost:8000/parse/pdf \
  -F "file=@your_cv.pdf"
```

#### 2. Parse Text CV
```
POST /parse/text
```
Parse CV text (đã trích xuất) → Returns JSON CV data

**Example:**
```bash
curl -X POST http://localhost:8000/parse/text \
  -H "Content-Type: application/json" \
  -d '{"cv_text": "Your CV text here..."}'
```

#### 3. Score CV Matching
```
POST /score
```
Chấm điểm CV với nhiều Job Descriptions

**Example:**
```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d @score_request.json
```

#### 4. Health Check
```
GET /health
```
Kiểm tra trạng thái server

## 📖 Ví dụ sử dụng

### Full workflow: PDF → Parse → Score

**Bước 1: Parse PDF CV**

```python
import requests

# Upload và parse PDF
with open("my_cv.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/parse/pdf",
        files={"file": f}
    )

cv_data = response.json()["cv_data"]
print(f"Parsed CV: {cv_data['name']}")
```

**Bước 2: Prepare Job Descriptions**

```python
job_descriptions = [
    {
        "title": "Backend Developer",
        "company": "Tech Corp",
        "requirements": [
            "3+ years Python experience",
            "Experience with FastAPI/Django"
        ],
        "responsibilities": [
            "Build REST APIs",
            "Design database schemas"
        ],
        "required_skills": ["Python", "FastAPI", "PostgreSQL"]
    },
    {
        "title": "Full Stack Developer",
        "company": "Startup XYZ",
        "requirements": ["Python", "React", "Docker"],
        "responsibilities": ["Develop features", "Deploy apps"],
        "required_skills": ["Python", "React", "AWS"]
    }
]
```

**Bước 3: Score CV Matching**

```python
# Score CV với jobs
score_request = {
    "cv": cv_data,
    "target_jobs": job_descriptions,
    "interaction_history": None  # Optional
}

response = requests.post(
    "http://localhost:8000/score",
    json=score_request
)

result = response.json()

# In kết quả
for match in result["job_matches"]:
    print(f"\n{match['job_title']} - {match['company']}")
    print(f"Overall Score: {match['overall_score']}/100")
    print(f"Skills Match: {match['skills_match_score']}/100")
    print(f"Strengths: {match['strengths']}")
    print(f"Gaps: {match['gaps']}")
    print(f"Suggestions: {match['suggestions']}")
```

### Interactive Learning (LGIR)

```python
# User có lịch sử tương tác
interaction_history = {
    "job_descriptions": [
        # 5 jobs user đã xem/apply
        {...}, {...}, {...}, {...}, {...}
    ],
    "interaction_count": 5
}

score_request = {
    "cv": cv_data,
    "target_jobs": new_jobs,
    "interaction_history": interaction_history
}

# LGIR sẽ:
# 1. Phân loại user (few-shot vs many-shot)
# 2. Interactive resume completion (suy luận skills ngầm định)
# 3. Quality detection
# 4. GAN refinement (nếu cần)
# 5. Scoring với enhanced resume
```

## 🌐 Deploy

### Deploy lên AWS EC2

1. **Launch EC2 instance**
   - Ubuntu 22.04
   - t2.medium hoặc cao hơn
   - Mở port 8000 trong Security Group

2. **SSH vào EC2**
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

3. **Setup server**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3-pip python3-venv -y

# Clone repo
git clone <your-repo-url>
cd KLTN

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements_production.txt

# Create .env file
nano .env
# Paste your OPENAI_API_KEY
```

4. **Run with systemd**

Tạo file `/etc/systemd/system/lgir-api.service`:

```ini
[Unit]
Description=LGIR CV Matching API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/KLTN
Environment="PATH=/home/ubuntu/KLTN/venv/bin"
EnvironmentFile=/home/ubuntu/KLTN/.env
ExecStart=/home/ubuntu/KLTN/venv/bin/python server_production.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl daemon-reload
sudo systemctl start lgir-api
sudo systemctl enable lgir-api

# Check status
sudo systemctl status lgir-api
```

5. **Setup Nginx (Optional)**

```bash
sudo apt install nginx -y
```

Tạo file `/etc/nginx/sites-available/lgir-api`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/lgir-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Deploy lên Heroku

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create your-app-name

# Set env vars
heroku config:set OPENAI_API_KEY=your-key

# Deploy
git push heroku main

# Open app
heroku open
```

## 🛠️ Công nghệ

### Backend
- **FastAPI**: Modern Python web framework
- **OpenAI GPT-4o-mini**: LLM cho parsing và scoring
- **PDFPlumber**: PDF text extraction
- **Uvicorn**: ASGI server

### AI/ML
- **LGIR Methodology**: Learning from Generative Interactions
  - Resume Completion (Simple + Interactive)
  - Quality Detection
  - GAN-based Refinement
  - Deterministic Scoring

### Dependencies
Xem chi tiết trong `requirements_production.txt`:
- fastapi
- uvicorn
- openai
- pdfplumber
- pydantic
- python-multipart

## 📁 Cấu trúc project

```
KLTN/
├── server_production.py          # Main API server
├── pdf_cv_parser_enhanced.py     # CV parsing utilities
├── requirements_production.txt    # Python dependencies
├── requirements_lgir.txt         # LGIR-specific dependencies
├── requirements_parser.txt       # Parser-specific dependencies
├── Dockerfile                    # Docker configuration
├── docker-compose.yml           # Docker Compose setup
├── config.env.example           # Environment variables template
├── .env                         # Environment variables (DO NOT COMMIT)
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## 🔒 Bảo mật

- **KHÔNG commit file `.env`** lên Git
- Sử dụng `.gitignore` để bảo vệ secrets
- Rotate OpenAI API keys định kỳ
- Giới hạn CORS origins khi deploy production
- Sử dụng HTTPS cho production

## 📝 License

MIT License - Tự do sử dụng và chỉnh sửa

## 👤 Author

Nguyễn Hồng Hiệp

## 🤝 Contributing

Mọi đóng góp đều được hoan nghênh! Tạo Pull Request hoặc Issue nếu bạn có ý tưởng cải thiện.

---

**Happy Coding! 🚀**

