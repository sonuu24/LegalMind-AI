# 🚀 LexPilot Deployment Guide

**Complete deployment guide for MCP Legal Assistant (LexPilot)**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Local Development](#local-development)
5. [Production Deployment](#production-deployment)
6. [Docker Deployment](#docker-deployment)
7. [Cloud Deployment](#cloud-deployment)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.10+** (3.11 or 3.12 recommended)
- **OpenAI API Key** - Get from [platform.openai.com](https://platform.openai.com)
- **Anthropic API Key** - Get from [console.anthropic.com](https://console.anthropic.com)

### Optional (for full features)

- **PostgreSQL 14+** - For persistent storage
- **Pinecone API Key** - For vector search
- **Google Calendar API** - For deadline tracking
- **Twilio** - For SMS alerts
- **Stripe** - For billing

---

## Quick Start

### 1. Clone & Install

```bash
# Clone repository
git clone https://github.com/daniellopez882/LexMind-Legal.git
cd "MCP LEGAL ASSISTANT AGENT"

# Create virtual environment
python -m venv venv

# Activate environment
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY, ANTHROPIC_API_KEY
```

### 3. Start Server

```bash
# Start FastAPI server
python main.py serve

# Or with auto-reload (development)
python main.py serve --reload
```

### 4. Test API

```bash
# Health check
curl http://localhost:8000/health

# Review a contract
curl -X POST http://localhost:8000/api/v1/contract/review \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "SAMPLE CONTRACT TEXT",
    "document_name": "Test.pdf",
    "matter_id": "M-001",
    "client_name": "Test Client",
    "jurisdiction": "Delaware"
  }'
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ============================================================
# REQUIRED - LLM API Keys
# ============================================================
OPENAI_API_KEY=sk-your-actual-openai-key
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key

# ============================================================
# OPTIONAL - Pinecone (Vector Search)
# ============================================================
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-west-2
PINECONE_INDEX_NAME=legal-assistant-index

# ============================================================
# OPTIONAL - PostgreSQL (Persistent Storage)
# ============================================================
DATABASE_URL=postgresql://user:password@localhost:5432/legal_assistant
DATABASE_ASYNC_URL=postgresql+asyncpg://user:password@localhost:5432/legal_assistant

# ============================================================
# OPTIONAL - Google Calendar (Deadlines)
# ============================================================
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_CALENDAR_ID=primary

# ============================================================
# OPTIONAL - Twilio (SMS Alerts)
# ============================================================
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# ============================================================
# OPTIONAL - Stripe (Billing)
# ============================================================
STRIPE_SECRET_KEY=sk_live_your-stripe-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# ============================================================
# SERVER CONFIGURATION
# ============================================================
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info  # debug, info, warning, error

# ============================================================
# SECURITY (Change in production!)
# ============================================================
SECRET_KEY=your-super-secret-key-min-32-chars
ENCRYPTION_KEY=your-32-byte-encryption-key

# ============================================================
# DEFAULTS
# ============================================================
DEFAULT_JURISDICTION=Texas
DEFAULT_BILLING_INCREMENT=0.1
```

---

## Local Development

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking (optional)
mypy src/
```

### Development Server

```bash
# With auto-reload
python main.py serve --reload --port 8000

# MCP Server (separate terminal)
python main.py mcp
```

### CLI Commands

```bash
# Review contract
python main.py review-contract \
  --contract agreement.pdf \
  --matter-id M-001 \
  --client "Acme Corp" \
  --jurisdiction Delaware

# Legal research
python main.py research \
  --question "What is the statute of limitations for breach of contract?" \
  --jurisdiction Texas \
  --practice-area Contract \
  --matter-id M-002 \
  --client "Test Client"

# Draft document
python main.py draft \
  --type NDA \
  --matter-id M-003 \
  --client "StartupXYZ" \
  --jurisdiction California

# List templates
python main.py templates
```

---

## Production Deployment

### 1. Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `LOG_LEVEL=warning` or `error`
- [ ] Configure CORS origins (don't use `*`)
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Rotate API keys
- [ ] Enable database backups
- [ ] Set up monitoring/alerting

### 2. Generate Secret Key

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Configure CORS

Edit `src/server/server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 4. Run with Production Server

```bash
# Using uvicorn directly
uvicorn src.server.server:create_app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop \
  --http httptools

# Or using gunicorn (Linux)
gunicorn src.server.server:create_app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120
```

### 5. Process Manager (systemd)

Create `/etc/systemd/system/lexpilot.service`:

```ini
[Unit]
Description=LexPilot Legal Assistant API
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/lexpilot
Environment="PATH=/opt/lexpilot/venv/bin"
ExecStart=/opt/lexpilot/venv/bin/uvicorn src.server.server:create_app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable lexpilot
sudo systemctl start lexpilot
sudo systemctl status lexpilot
```

---

## Docker Deployment

### 1. Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 lexpilot && chown -R lexpilot:lexpilot /app
USER lexpilot

EXPOSE 8000

CMD ["uvicorn", "src.server.server:create_app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=postgresql://lexpilot:password@db:5432/legal_assistant
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_USER=lexpilot
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=legal_assistant
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### 3. Build & Run

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

---

## Cloud Deployment

### AWS Deployment

#### Option 1: EC2

```bash
# Launch EC2 instance (t3.medium minimum)
# Install Docker
# Deploy using docker-compose (above)
```

#### Option 2: ECS Fargate

```yaml
# task-definition.json
{
  "family": "lexpilot",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "lexpilot",
      "image": "your-ecr-repo/lexpilot:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "OPENAI_API_KEY", "value": "xxx"},
        {"name": "ANTHROPIC_API_KEY", "value": "xxx"}
      ]
    }
  ]
}
```

### Google Cloud Platform

#### Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/lexpilot

# Deploy to Cloud Run
gcloud run deploy lexpilot \
  --image gcr.io/PROJECT_ID/lexpilot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=xxx,ANTHROPIC_API_KEY=xxx
```

### Azure

#### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name lexpilot \
  --image your-registry/lexpilot:latest \
  --dns-name-label lexpilot \
  --ports 8000 \
  --environment-variables \
    OPENAI_API_KEY=xxx \
    ANTHROPIC_API_KEY=xxx
```

---

## Testing

### Run Test Suite

```bash
# All tests
pytest tests/ -v

# With coverage
pytest --cov=src --cov-report=html --cov-report=term

# Specific test class
pytest tests/test_api.py::TestContractReview -v

# Integration tests
pytest tests/test_api.py::TestIntegration -v
```

### API Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Contract review
curl -X POST http://localhost:8000/api/v1/contract/review \
  -H "Content-Type: application/json" \
  -d '{"document_text":"SAMPLE","document_name":"Test.pdf","matter_id":"M-001","client_name":"Client","jurisdiction":"Delaware"}'

# Legal research
curl -X POST http://localhost:8000/api/v1/case/research \
  -H "Content-Type: application/json" \
  -d '{"legal_question":"Statute of limitations for breach of contract?","jurisdiction":"Texas","practice_area":"Contract","matter_id":"M-001","client_name":"Client"}'

# Document drafting
curl -X POST http://localhost:8000/api/v1/document/draft \
  -H "Content-Type: application/json" \
  -d '{"document_type":"NDA","party_details":{"party_a":"A","party_b":"B"},"jurisdiction":"Delaware","matter_id":"M-001","client_name":"Client"}'
```

### Load Testing

```bash
# Install locust
pip install locust

# Create locustfile.py and run
locust -f locustfile.py --host http://localhost:8000
```

---

## Troubleshooting

### Common Issues

#### 1. Module Not Found

```bash
# Ensure you're in the project directory
cd "MCP LEGAL ASSISTANT AGENT"

# Ensure virtual environment is activated
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 2. API Key Errors

```bash
# Check .env file exists
ls -la .env

# Verify API keys are set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Test API keys
python -c "import os; from src.config import get_settings; s=get_settings(); print(s.openai_api_key)"
```

#### 3. Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U lexpilot -d legal_assistant

# Check DATABASE_URL format
# postgresql://user:password@host:port/database
```

#### 4. Port Already in Use

```bash
# Find process using port 8000
# Windows:
netstat -ano | findstr :8000
# Linux/Mac:
lsof -i :8000

# Use different port
python main.py serve --port 8001
```

#### 5. Import Errors

```bash
# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or install in development mode
pip install -e .
```

### Logs

```bash
# View application logs
# If using systemd:
journalctl -u lexpilot -f

# If using Docker:
docker-compose logs -f api

# If running directly:
# Logs appear in terminal
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug
python main.py serve --reload
```

---

## Monitoring & Observability

### Health Checks

```bash
# Health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0","timestamp":"2026-03-07T..."}
```

### Metrics to Monitor

- **API Response Time** - Should be < 2s for most endpoints
- **Error Rate** - Should be < 1%
- **LLM API Usage** - Monitor token consumption
- **Database Connections** - Monitor pool usage
- **Memory Usage** - Should be stable

### Logging

Logs are written to stdout/stderr. Configure log aggregation:

- **AWS**: CloudWatch Logs
- **GCP**: Cloud Logging
- **Azure**: Application Insights
- **Self-hosted**: ELK Stack, Loki

---

## Security Best Practices

1. **API Keys**: Store in environment variables, never in code
2. **HTTPS**: Always use TLS in production
3. **Authentication**: Enable JWT auth for protected endpoints
4. **Rate Limiting**: Implement rate limiting (e.g., slowapi)
5. **Input Validation**: All inputs validated via Pydantic
6. **Database**: Use connection pooling, parameterized queries
7. **Secrets**: Rotate secrets regularly
8. **Backups**: Daily database backups
9. **Updates**: Keep dependencies updated
10. **Audit**: Log all API requests

---

## Support

**Documentation**: [GitHub Wiki](https://github.com/daniellopez882/LexMind-Legal/wiki)  
**Issues**: [GitHub Issues](https://github.com/daniellopez882/LexMind-Legal/issues)  
**Email**: agentic.ai.engineer@example.com

---

<div align="center">

**Ready to deploy? Run these commands:**

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py serve
```

[⬆ Back to top](#-lexpilot-deployment-guide)

</div>
