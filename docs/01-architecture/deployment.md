# Deployment Architecture

## Table of Contents
- [Overview](#overview)
- [Local Development Setup](#local-development-setup)
- [Production Architecture](#production-architecture)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [External Services](#external-services)
- [Frontend Deployment](#frontend-deployment)
- [Backend Deployment](#backend-deployment)
- [Monitoring & Logging](#monitoring--logging)
- [Scaling Strategy](#scaling-strategy)
- [Security Considerations](#security-considerations)
- [CI/CD Pipeline](#cicd-pipeline)

---

## Overview

VoltPulse SG employs a **cloud-native, microservices architecture** with managed services to minimize operational overhead. The deployment strategy prioritizes **developer velocity**, **cost efficiency**, and **horizontal scalability**.

### Deployment Stack

```mermaid
---
id: 9f8e7d6a-5c4b-4a3e-9f2d-8e7a6c5b4d3f
---
graph TB
    subgraph Frontend Deployment
        A[Vercel] --> B[Next.js 15 SSR]
        B --> C[CDN Edge<br/>Global]
    end

    subgraph Backend Deployment
        D[Cloud VM<br/>Ubuntu 22.04] --> E[FastAPI<br/>Uvicorn]
        E --> F[Nginx<br/>Reverse Proxy]
    end

    subgraph Managed Services
        G[Supabase<br/>PostgreSQL]
        H[Ollama Cloud<br/>LLM]
        I[OpenAI API<br/>Vision]
        J[SEALION API<br/>Embeddings]
    end

    C -->|API Calls| F
    E --> G
    E --> H
    E --> I
    E --> J

    style Frontend Deployment fill:#61dafb,color:#000
    style Backend Deployment fill:#009688,color:#fff
    style Managed Services fill:#ff9800,color:#fff
```

---

## Local Development Setup

### Prerequisites

**Required**:
- **Node.js** 18+ and npm
- **Python** 3.11+
- **Git**
- **PostgreSQL** 15+ (or Supabase account)

**Recommended**:
- **Visual Studio Code** with extensions:
  - Python
  - ESLint
  - Tailwind CSS IntelliSense
- **Postman** for API testing

### Frontend Setup

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/VoltPulse-SG.git
cd VoltPulse-SG/frontend
```

#### 2. Install Dependencies
```bash
npm install
```

**Installs**:
- Next.js 15, React 19, TypeScript 5.7
- Tailwind CSS, Leaflet, Recharts
- ~1,200 packages total (~400MB `node_modules`)

#### 3. Configure Environment

Create `.env.local`:
```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Note**: `NEXT_PUBLIC_` prefix exposes variables to browser.

#### 4. Run Development Server
```bash
npm run dev
```

**Outputs**:
```
> voltpulse-frontend@0.1.0 dev
> next dev

  ▲ Next.js 15.1.0
  - Local:        http://localhost:3000
  - Environments: .env.local

✓ Ready in 2.3s
```

**Hot Reload**: Enabled - changes reflect immediately

### Backend Setup

#### 1. Navigate to Backend
```bash
cd ../backend
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Installs**:
- FastAPI, Uvicorn, Pydantic
- LangGraph, LangChain, psycopg
- NumPy, SciPy, OpenAI
- ~50 packages total (~300MB)

#### 4. Configure Environment

Create `.env`:
```env
# Ollama LLM
OLLAMA_API_KEY=your_ollama_api_key
OLLAMA_BASE_URL=https://your-ollama-endpoint

# Supabase Database
SUPABASE_DB_HOST=your-supabase-host.supabase.co
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.your-project-ref
SUPABASE_DB_PASSWORD=your-secure-password
SUPABASE_DB_SSLMODE=require

# SeaLion Encoder
SEALION_ENDPOINT=https://your-sealion-endpoint

# Tavily Web Search
TAVILY_API_KEY=your_tavily_api_key

# OpenAI Vision
OPENAI_API_KEY=sk-your-openai-api-key
```

**Security**: Never commit `.env` to Git (`.gitignore` entry required)

#### 5. Run Development Server
```bash
uvicorn app:app --reload --port 8000
```

**Outputs**:
```
INFO:     Will watch for changes in these directories: ['d:\\VoltPulse-SG\\backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Auto-Reload**: Enabled - code changes trigger restart

### Database Setup (Local)

#### Option 1: Supabase (Recommended)

**Create Project**:
1. Visit [supabase.com](https://supabase.com)
2. Create new project
3. Note database credentials

**Enable pgvector**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Create Tables**:
```sql
CREATE TABLE my_embeddings (
    source_id TEXT PRIMARY KEY,
    text_content JSONB,
    metadata JSONB,
    embedding VECTOR(1024),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON my_embeddings USING ivfflat (embedding vector_l2_ops)
WITH (lists=100);
```

**Seed Data** (optional):
```bash
python scripts/seed_retailers.py
```

#### Option 2: Local PostgreSQL

**Install PostgreSQL 15**:
```bash
# Ubuntu/Debian
sudo apt install postgresql-15 postgresql-contrib

# macOS
brew install postgresql@15
```

**Install pgvector**:
```bash
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**Create Database**:
```sql
CREATE DATABASE voltpulse;
\c voltpulse
CREATE EXTENSION vector;
```

**Update `.env`**:
```env
SUPABASE_DB_HOST=localhost
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=voltpulse
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=yourpassword
SUPABASE_DB_SSLMODE=prefer
```

### Verification

#### Test Frontend
Visit `http://localhost:3000`:
- Upload page renders
- Analytics page loads (with placeholder data)
- Chat interface responds

#### Test Backend
Visit `http://localhost:8000/docs`:
- OpenAPI docs display
- Test `/health` endpoint
- Try POST `/ocr/process` with sample image

---

## Production Architecture

### Infrastructure Diagram

```mermaid
---
id: 8e7f9d6a-5c4b-4a3e-9f2d-8e7a6c5b4d3f
---
graph TB
    subgraph CDN Layer
        A[Cloudflare/Vercel CDN] --> B[Static Assets<br/>Images, JS, CSS]
    end

    subgraph Application Layer
        C[Vercel Edge<br/>Next.js SSR] --> D[API Routes]
        D --> E[Backend LB<br/>Nginx]
    end

    subgraph Backend Cluster
        E --> F1[FastAPI Instance 1]
        E --> F2[FastAPI Instance 2]
        E --> F3[FastAPI Instance N]
    end

    subgraph Data Layer
        G[Supabase<br/>Primary]
        H[Supabase<br/>Read Replica]
        I[Redis<br/>Cache Layer]
    end

    F1 --> G
    F2 --> G
    F3 --> G
    F1 --> I
    F2 --> I
    F3 --> I
    G --> H

    subgraph External APIs
        J[Ollama Cloud]
        K[OpenAI API]
        L[SEALION API]
        M[Tavily API]
    end

    F1 --> J
    F1 --> K
    F1 --> L
    F1 --> M

    style CDN Layer fill:#61dafb,color:#000
    style Application Layer fill:#009688,color:#fff
    style Backend Cluster fill:#4caf50,color:#fff
    style Data Layer fill:#3ecf8e,color:#fff
    style External APIs fill:#ff9800,color:#fff
```

### Component Responsibilities

| Component | Purpose | Scaling | Cost |
|-----------|---------|---------|------|
| **Vercel Edge** | SSR, routing, CDN | Auto-scale (serverless) | $20/mo (Pro) |
| **Nginx** | Load balancer, SSL termination | Manual | Free |
| **FastAPI Instances** | API logic, LLM orchestration | Horizontal (2-10 instances) | $10-50/mo |
| **Supabase** | Database, pgvector | Auto-scale compute | $25-100/mo |
| **Redis** (future) | Session cache, rate limiting | Single instance | $15/mo |

---

## Environment Configuration

### Frontend Environment Variables

**File**: `frontend/.env.production`

```env
# Public (exposed to browser)
NEXT_PUBLIC_API_URL=https://api.voltpulse.sg

# Private (server-side only)
# None currently
```

**Deployment**:
- Set in Vercel dashboard: Settings → Environment Variables
- Automatically injected at build time

### Backend Environment Variables

**File**: `backend/.env.production`

```env
# Ollama LLM
OLLAMA_API_KEY=${OLLAMA_API_KEY}
OLLAMA_BASE_URL=https://cloud.ollama.com

# Supabase Database
SUPABASE_DB_HOST=${SUPABASE_DB_HOST}
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=${SUPABASE_DB_USER}
SUPABASE_DB_PASSWORD=${SUPABASE_DB_PASSWORD}
SUPABASE_DB_SSLMODE=require

# Connection Pool Settings
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
DB_POOL_TIMEOUT=30

# SeaLion Encoder
SEALION_ENDPOINT=${SEALION_ENDPOINT}

# OpenAI
OPENAI_API_KEY=${OPENAI_API_KEY}

# Tavily
TAVILY_API_KEY=${TAVILY_API_KEY}

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=production
ALLOWED_ORIGINS=https://voltpulse.sg,https://www.voltpulse.sg
```

**Secret Management**:
- Store in **GitHub Secrets** for CI/CD
- Use **AWS Secrets Manager** or **HashiCorp Vault** for production
- **Never** commit to Git

---

## Database Setup

### Supabase Configuration

#### 1. Create Production Project

**Settings**:
- **Region**: Singapore (ap-southeast-1)
- **Pricing**: Pro plan ($25/mo)
- **Compute**: 2GB RAM (expandable to 8GB)

#### 2. Enable Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search
```

#### 3. Create Tables

**Embeddings Table**:
```sql
CREATE TABLE my_embeddings (
    source_id TEXT PRIMARY KEY,
    text_content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding VECTOR(1024),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_metadata_form_type ON my_embeddings ((metadata->>'form_type'));
CREATE INDEX idx_created_at ON my_embeddings (created_at DESC);

-- Vector index (IVFFlat)
CREATE INDEX idx_embedding_ivfflat ON my_embeddings
USING ivfflat (embedding vector_l2_ops)
WITH (lists=100);
```

**LangGraph Tables** (auto-created by LangGraph):
```sql
-- Checkpoints (conversation state)
CREATE TABLE langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint BYTEA NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- Store (semantic memory)
CREATE TABLE langgraph_store (
    namespace TEXT[] NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (namespace, key)
);
```

#### 4. Configure Connection Pooling

**Supabase Dashboard**:
- Settings → Database → Connection Pooling
- **Mode**: Transaction
- **Pool Size**: 15

**PgBouncer Settings**:
```ini
pool_mode = transaction
max_client_conn = 100
default_pool_size = 15
reserve_pool_size = 5
```

#### 5. Backup Configuration

**Automated Backups**:
- **Frequency**: Daily at 2:00 AM UTC
- **Retention**: 7 days (Pro plan)
- **Point-in-Time Recovery**: Enabled (up to 7 days)

**Manual Backup**:
```bash
pg_dump postgresql://user:pass@host:6543/postgres > backup.sql
```

---

## External Services

### Ollama Cloud

**Setup**:
1. Sign up at [ollama.com](https://ollama.com)
2. Create API key
3. Note endpoint URL

**Model**: GPT-OSS 120B
**Cost**: $0.50 per 1M tokens (~$0.02/query)

**Configuration**:
```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    base_url=os.getenv("OLLAMA_BASE_URL"),
    api_key=os.getenv("OLLAMA_API_KEY"),
    model="gpt-oss-120b",
    temperature=0.1
)
```

### OpenAI API

**Setup**:
1. Create account at [platform.openai.com](https://platform.openai.com)
2. Generate API key
3. Add payment method

**Model**: `gpt-4o` (Vision)
**Cost**: $5 per 1M input tokens (~$0.014/bill)

**Usage Limits**:
- **Tier 1**: $100/month (default)
- **Tier 2**: $500/month (after $5 spent)

### SEALION API

**Setup**:
1. Contact SEALION team for access
2. Receive endpoint URL + credentials
3. Test with sample request

**Cost**: $0.001 per 1K embeddings (130× cheaper than OpenAI)

**Endpoint**:
```
POST https://your-sealion-endpoint/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Analysis prompt..."}
  ]
}
```

### Tavily API

**Setup**:
1. Sign up at [tavily.com](https://tavily.com)
2. Get API key
3. Choose plan

**Cost**:
- **Free**: 1,000 searches/month
- **Basic**: $29/mo (20K searches)

---

## Frontend Deployment

### Vercel Deployment

#### 1. Connect Repository

**Vercel Dashboard**:
1. Import Git Repository
2. Select `frontend` directory as root
3. Framework: Next.js

#### 2. Build Settings

**Configuration**:
```yaml
Framework Preset: Next.js
Build Command: npm run build
Output Directory: .next
Install Command: npm install
Development Command: npm run dev
```

**Build Performance**:
- Build Time: ~2 minutes
- Bundle Size: ~500KB (gzipped)

#### 3. Environment Variables

**Add in Dashboard**:
```
NEXT_PUBLIC_API_URL = https://api.voltpulse.sg
```

#### 4. Custom Domain

**DNS Configuration**:
```
Type  Name              Value
A     voltpulse.sg      76.76.21.21 (Vercel IP)
CNAME www.voltpulse.sg cname.vercel-dns.com
```

**SSL**: Auto-provisioned by Vercel (Let's Encrypt)

#### 5. Deployment Triggers

**Automatic Deployment**:
- **Production**: Push to `main` branch
- **Preview**: Push to any branch (creates preview URL)

**Manual Deployment**:
```bash
npm install -g vercel
vercel --prod
```

### Build Optimization

**Next.js Config** (`next.config.js`):
```javascript
module.exports = {
  reactStrictMode: true,
  swcMinify: true,  // Use SWC minifier (faster)
  images: {
    domains: ['supabase.co'],  // For Supabase images
  },
  experimental: {
    optimizeCss: true,  // Optimize CSS
  },
  // Reduce bundle size
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
}
```

**Performance Metrics**:
- **First Contentful Paint**: < 1s
- **Time to Interactive**: < 2s
- **Lighthouse Score**: 95+

---

## Backend Deployment

### Cloud VM Setup (Ubuntu 22.04)

#### 1. Provision VM

**Providers**: AWS EC2, DigitalOcean, Linode

**Recommended Specs**:
- **Instance**: t3.medium (2 vCPU, 4GB RAM)
- **Storage**: 30GB SSD
- **Network**: 3TB/month bandwidth
- **Cost**: ~$35/month

#### 2. Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Nginx
sudo apt install nginx -y

# Install Git
sudo apt install git -y

# Create app user
sudo useradd -m -s /bin/bash voltpulse
sudo usermod -aG sudo voltpulse
```

#### 3. Clone Repository

```bash
sudo su - voltpulse
git clone https://github.com/your-org/VoltPulse-SG.git
cd VoltPulse-SG/backend
```

#### 4. Install Dependencies

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. Configure Environment

```bash
nano .env
# Paste production environment variables
```

#### 6. Setup Systemd Service

Create `/etc/systemd/system/voltpulse.service`:
```ini
[Unit]
Description=VoltPulse FastAPI Application
After=network.target

[Service]
Type=notify
User=voltpulse
Group=voltpulse
WorkingDirectory=/home/voltpulse/VoltPulse-SG/backend
Environment="PATH=/home/voltpulse/VoltPulse-SG/backend/venv/bin"
EnvironmentFile=/home/voltpulse/VoltPulse-SG/backend/.env
ExecStart=/home/voltpulse/VoltPulse-SG/backend/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and Start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable voltpulse
sudo systemctl start voltpulse
sudo systemctl status voltpulse
```

#### 7. Configure Nginx

Create `/etc/nginx/sites-available/voltpulse`:
```nginx
upstream voltpulse_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.voltpulse.sg;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.voltpulse.sg;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.voltpulse.sg/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.voltpulse.sg/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # CORS
    add_header Access-Control-Allow-Origin "https://voltpulse.sg" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    # Client body size (for bill uploads)
    client_max_body_size 10M;

    location / {
        proxy_pass http://voltpulse_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for LLM calls
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

**Enable Site**:
```bash
sudo ln -s /etc/nginx/sites-available/voltpulse /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 8. SSL Certificate

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.voltpulse.sg
```

**Auto-renewal** (cron):
```bash
0 3 * * * certbot renew --quiet
```

---

## Monitoring & Logging

### Application Logs

**Systemd Logs**:
```bash
# View logs
sudo journalctl -u voltpulse -f

# Last 100 lines
sudo journalctl -u voltpulse -n 100
```

**Log Rotation**:
```bash
# /etc/logrotate.d/voltpulse
/var/log/voltpulse/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 voltpulse voltpulse
}
```

### Performance Monitoring

**Tools**:
- **Uptime Kuma** - Self-hosted uptime monitoring
- **Grafana + Prometheus** - Metrics dashboards
- **Sentry** - Error tracking

**Example**: Sentry Integration

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://your-sentry-dsn",
    integrations=[FastApiIntegration()],
    environment="production",
    traces_sample_rate=0.1
)
```

### Database Monitoring

**Supabase Dashboard**:
- Query Performance
- Connection Pool Usage
- Storage Usage
- Replication Lag (if read replica enabled)

**Custom Queries**:
```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Slow queries
SELECT query, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Scaling Strategy

### Horizontal Scaling

```mermaid
---
id: 7d9f8e6a-5c4b-4a3e-9f2d-8e7a6c5b4d3f
---
graph TB
    A[Load Balancer<br/>Nginx] --> B[Instance 1<br/>4GB RAM]
    A --> C[Instance 2<br/>4GB RAM]
    A --> D[Instance 3<br/>4GB RAM]

    B --> E[(Database<br/>Connection Pool)]
    C --> E
    D --> E

    E --> F[Supabase<br/>Read Replica]

    style A fill:#009688,color:#fff
    style B fill:#4caf50,color:#fff
    style C fill:#4caf50,color:#fff
    style D fill:#4caf50,color:#fff
    style E fill:#3ecf8e,color:#fff
```

**Capacity Planning**:
| Metric | 1 Instance | 2 Instances | 3 Instances |
|--------|-----------|-------------|-------------|
| **Requests/sec** | 50 | 100 | 150 |
| **Concurrent Users** | 100 | 200 | 300 |
| **Database Connections** | 10 | 20 | 30 |

### Vertical Scaling

**When to Scale Up**:
- CPU usage consistently > 70%
- Memory usage > 80%
- Request latency > 2s

**Upgrade Path**:
1. **t3.medium** (2 vCPU, 4GB) → $35/mo
2. **t3.large** (2 vCPU, 8GB) → $70/mo
3. **t3.xlarge** (4 vCPU, 16GB) → $140/mo

### Caching Strategy (Future)

**Redis Implementation**:
```python
import redis

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# Cache retailer search results
cache_key = f"retailers:{product}:{location}"
cached = redis_client.get(cache_key)
if cached:
    return json.loads(cached)

# Execute search, then cache
results = search_retailers(product, location)
redis_client.setex(cache_key, 900, json.dumps(results))  # 15 min TTL
```

---

## Security Considerations

### API Security

**Rate Limiting** (future):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request):
    # ...
```

**Authentication** (future):
```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials: HTTPCredentials = Security(security)):
    if credentials.credentials != os.getenv("API_TOKEN"):
        raise HTTPException(status_code=403, detail="Invalid token")
    return credentials.credentials
```

### Database Security

**SSL/TLS**:
- All connections use `sslmode=require`
- Certificates validated

**Row-Level Security** (future):
```sql
ALTER TABLE my_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation ON my_embeddings
    FOR ALL
    USING (metadata->>'user_id' = current_setting('app.user_id'));
```

### Secrets Management

**AWS Secrets Manager**:
```bash
aws secretsmanager get-secret-value --secret-id voltpulse/production
```

**Python Integration**:
```python
import boto3
import json

client = boto3.client('secretsmanager', region_name='ap-southeast-1')
response = client.get_secret_value(SecretId='voltpulse/production')
secrets = json.loads(response['SecretString'])

OPENAI_API_KEY = secrets['OPENAI_API_KEY']
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run tests
        run: |
          cd backend
          pytest

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: voltpulse
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd VoltPulse-SG
            git pull origin main
            cd backend
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart voltpulse
```

**Secrets** (GitHub Settings):
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `SERVER_HOST`
- `SSH_PRIVATE_KEY`

### Deployment Checklist

**Before Deploy**:
- [ ] Run tests locally
- [ ] Update environment variables
- [ ] Database migrations (if any)
- [ ] Backup database
- [ ] Review dependency updates

**After Deploy**:
- [ ] Verify health endpoints
- [ ] Test critical flows (upload, chat)
- [ ] Monitor error logs (30 minutes)
- [ ] Check performance metrics

---

## Summary

VoltPulse SG's deployment architecture prioritizes:

### ✅ Simplicity
- **Managed Services** - Supabase, Vercel, Ollama Cloud
- **Minimal DevOps** - No Kubernetes, no complex orchestration
- **Automated Deployments** - GitHub Actions CI/CD

### ✅ Cost Efficiency
- **Total Monthly Cost**: ~$100-150
  - Frontend (Vercel): $20
  - Backend (VM): $35
  - Database (Supabase): $25
  - APIs (OpenAI, Ollama, etc.): $20-50

### ✅ Scalability
- **Horizontal Scaling** - Add FastAPI instances
- **Vertical Scaling** - Upgrade VM size
- **Database Scaling** - Supabase auto-scales
- **CDN Edge** - Global distribution via Vercel

### ✅ Reliability
- **99.9% Uptime** - Target SLA
- **Automated Backups** - Daily database snapshots
- **SSL/TLS** - All connections encrypted
- **Monitoring** - Logs, metrics, alerts

**Deployment Time**:
- Initial setup: 2-3 hours
- Code deploy: 5-10 minutes (automated)
- Rollback: < 2 minutes

**Related Documentation**:
- [System Overview](./overview.md) - Architecture diagrams
- [Tech Stack](./tech-stack.md) - Technology details
- [Data Flow](./data-flow.md) - Request/response flows
- [Environment Variables](../07-appendices/environment-variables.md) - Complete .env reference
