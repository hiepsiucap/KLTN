# 🚀 Hướng dẫn Setup CI/CD

## Tổng quan

```
Push code → GitHub Actions → Build Docker → Push Docker Hub → SSH EC2 → Deploy
```

## 📋 Bước 1: Tạo Docker Hub Account

1. Đăng ký tại https://hub.docker.com
2. Tạo repository mới: `lgir-parser`
3. Lấy username và tạo Access Token:
   - Vào Account Settings → Security → Access Tokens
   - Tạo token với quyền Read/Write

## 📋 Bước 2: Setup GitHub Secrets

Vào repo GitHub → Settings → Secrets and variables → Actions → New repository secret

Thêm các secrets sau:

| Secret Name | Giá trị | Mô tả |
|-------------|---------|-------|
| `DOCKER_USERNAME` | your-dockerhub-username | Docker Hub username |
| `DOCKER_PASSWORD` | dckr_pat_xxxx | Docker Hub Access Token |
| `EC2_HOST` | 54.123.456.789 | IP public của EC2 |
| `EC2_USERNAME` | ubuntu | User SSH (thường là ubuntu hoặc ec2-user) |
| `EC2_SSH_KEY` | -----BEGIN OPENSSH PRIVATE KEY----- ... | Private key SSH (toàn bộ nội dung file .pem) |
| `OPENAI_API_KEY` | sk-proj-xxxx | OpenAI API Key |

## 📋 Bước 3: Setup EC2

### 3.1 Cài Docker trên EC2

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Add user to docker group
sudo usermod -aG docker $USER

# Logout và login lại
exit
```

### 3.2 Mở port 9000 trong Security Group

1. Vào AWS Console → EC2 → Security Groups
2. Chọn Security Group của EC2
3. Inbound rules → Edit → Add rule:
   - Type: Custom TCP
   - Port: 9000
   - Source: 0.0.0.0/0 (hoặc IP cụ thể)

### 3.3 (Optional) Setup OPENAI_API_KEY trên EC2

Nếu không muốn lưu API key trong GitHub Secrets:

```bash
# Thêm vào ~/.bashrc
echo 'export OPENAI_API_KEY="sk-proj-xxxx"' >> ~/.bashrc
source ~/.bashrc
```

## 📋 Bước 4: Test Deployment

### Chạy manual từ GitHub

1. Vào repo → Actions → "Deploy to EC2"
2. Click "Run workflow" → "Run workflow"

### Hoặc push code

```bash
git add .
git commit -m "Setup CI/CD"
git push origin main
```

## 🔧 Cấu hình Go Backend

Trong Go backend, set environment variable:

```bash
# .env hoặc docker-compose.yml
RESUME_PARSER_URL=http://localhost:9000
```

## 📊 Kiểm tra sau deploy

```bash
# SSH vào EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Kiểm tra container
docker ps

# Xem logs
docker logs lgir-parser

# Test health
curl http://localhost:9000/health
```

## ❓ Troubleshooting

### Container không start

```bash
# Xem logs
docker logs lgir-parser

# Kiểm tra port
sudo lsof -i :9000
```

### SSH connection refused

- Kiểm tra Security Group có mở port 22
- Kiểm tra SSH key đúng format

### Health check failed

- Kiểm tra OPENAI_API_KEY đã set đúng
- Xem logs để debug

## 🔄 Rollback

Nếu cần rollback về version cũ:

```bash
# List các image đã pull
docker images

# Run version cụ thể (dùng commit SHA)
docker run -d \
  --name lgir-parser \
  -p 9000:8000 \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  your-username/lgir-parser:abc123def
```

