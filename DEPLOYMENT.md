# Production Deployment Guide

This guide covers deploying the Bank Statement Analyzer to production.

## Pre-Deployment Checklist

- [ ] Test all features thoroughly with real data
- [ ] Customize categorization rules for your industry
- [ ] Review and test error handling
- [ ] Set up logging and monitoring
- [ ] Configure database backup strategy
- [ ] Set up security measures (rate limiting, etc.)
- [ ] Test export functionality
- [ ] Verify CORS configuration

## Backend Deployment

### Option 1: Heroku

```bash
# Install Heroku CLI
# Login to Heroku
heroku login

# Create app
heroku create bank-statement-analyzer

# Add Postgres database
heroku addons:create heroku-postgresql:standard-0

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

**Procfile** (create this file):
```
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --timeout 120
```

### Option 2: AWS EC2

```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install dependencies
sudo apt-get update
sudo apt-get install python3-pip python3-venv nginx supervisor

# Clone repo and setup
git clone your-repo
cd statementbur_python/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup Supervisor for process management
sudo nano /etc/supervisor/conf.d/bank_api.conf
```

**bank_api.conf**:
```ini
[program:bank_api]
directory=/home/ubuntu/statementbur_python/backend
command=/home/ubuntu/statementbur_python/backend/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/bank_api.log
```

**Nginx Configuration**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 3: DigitalOcean App Platform

```bash
# Connect via DigitalOcean CLI
doctl apps create --spec app.yaml

# Or use the DigitalOcean dashboard
```

**app.yaml**:
```yaml
name: bank-statement-analyzer
services:
- name: api
  github:
    repo: your-username/statementbur_python
    branch: main
  build_command: pip install -r backend/requirements.txt
  run_command: cd backend && uvicorn main:app --host 0.0.0.0 --port 8080
  http_port: 8080
  envs:
  - key: DATABASE_URL
    value: postgresql://${db.username}:${db.password}@${db.host}:5432/${db.name}
databases:
- engine: PG
  name: db
```

## Frontend Deployment

## OCR Dependencies (Tesseract & Poppler)

This project includes an optional local OCR fallback using Tesseract (via `pytesseract`) and `pdf2image` (requires Poppler).
Install the Python packages and the system binaries below during deployment if you want scanned PDFs to be processed locally.

- Python packages (already added to `backend/requirements.txt`):

```bash
# from the backend folder/venv
pip install -r backend/requirements.txt
# or install only OCR packages
pip install pytesseract pdf2image Pillow
```

- System binaries (required by `pytesseract` and `pdf2image`):

- Windows

  1. Install Tesseract OCR (recommended: UB Mannheim builds):

     - Download the installer: https://github.com/UB-Mannheim/tesseract/wiki
     - Run the installer and note the install path (e.g., `C:\Program Files\Tesseract-OCR`).

  2. Install Poppler for Windows (used by `pdf2image`) - get a release zip and extract:

     - https://github.com/oschwartz10612/poppler-windows/releases
     - Extract and note the `bin` folder path (e.g., `C:\tools\poppler-xx\bin`).

  3. Add both `Tesseract` and Poppler `bin` paths to your `PATH` environment variable or provide their paths to the library calls (examples below).

  Verification (PowerShell):

  ```powershell
  tesseract --version
  pdftoppm -v
  ```

  Example runtime configuration in Python (if not on PATH):

  ```python
  import pytesseract
  pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

  from pdf2image import convert_from_bytes
  images = convert_from_bytes(pdf_bytes, poppler_path=r"C:\tools\poppler-xx\bin")
  ```

- Ubuntu / Debian

  ```bash
  sudo apt-get update
  sudo apt-get install -y tesseract-ocr poppler-utils
  # Optional language packs (example for Afrikaans, French):
  # sudo apt-get install -y tesseract-ocr-afr tesseract-ocr-fra
  ```

  Verification:
  ```bash
  tesseract --version
  pdftoppm -v
  ```

- macOS (Homebrew)

  ```bash
  brew install tesseract poppler
  # Optional language packs via Homebrew or by installing traineddata files
  ```

  Verification:
  ```bash
  tesseract --version
  pdftoppm -v
  ```

- Notes on languages and accuracy

  - By default `pytesseract` uses the `eng` traineddata. To OCR other languages, install the appropriate Tesseract language packs and pass `lang="<code>"` to `pytesseract.image_to_string` or `ocr_pdf_bytes`.
  - Scanned PDFs with rotated pages or poor scan quality may require pre-processing (deskew, contrast) before OCR for better results.

- Quick Python sanity check

  ```python
  import pytesseract
  from pdf2image import convert_from_bytes

  print('tesseract:', pytesseract.get_tesseract_version())
  # convert a small PDF and OCR
  images = convert_from_bytes(open('sample.pdf','rb').read(), dpi=200)
  print('pages:', len(images))
  print(pytesseract.image_to_string(images[0]))
  ```

If you prefer cloud OCR instead of local Tesseract, see `DEPLOYMENT.md` notes or ask and I can add an optional cloud-provider section (Google Vision / Azure Computer Vision).

### Option 1: Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Login and deploy
cd frontend
vercel

# Set environment variable
vercel env add NEXT_PUBLIC_API_URL
# Enter your API URL: https://your-api-domain.com
```

### Option 2: Netlify

```bash
# Install Netlify CLI
npm i -g netlify-cli

cd frontend
netlify deploy --prod

# Or connect GitHub repo for auto-deploy
```

**netlify.toml**:
```toml
[build]
  command = "npm run build"
  publish = ".next/out"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[env]
  NEXT_PUBLIC_API_URL = "https://your-api-domain.com"
```

### Option 3: Docker + Your Server

**Dockerfile (frontend)**:
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY package.json .
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t bank-analyzer-frontend .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=https://your-api-domain.com \
  bank-analyzer-frontend
```

## Database Migration

### From SQLite to PostgreSQL

```python
# migration.py
from sqlalchemy import create_engine
from models import Base, Transaction

# SQLite to PostgreSQL
sqlite_engine = create_engine('sqlite:///./statement_analyzer.db')
pg_engine = create_engine('postgresql://user:password@localhost/bank_analyzer')

# Create tables in PostgreSQL
Base.metadata.create_all(pg_engine)

# Copy data
from sqlalchemy.orm import sessionmaker
SQLiteSession = sessionmaker(bind=sqlite_engine)
PGSession = sessionmaker(bind=pg_engine)

sqlite_session = SQLiteSession()
pg_session = PGSession()

transactions = sqlite_session.query(Transaction).all()
for txn in transactions:
    pg_session.add(txn)

pg_session.commit()
```

### Update Backend Environment Variable

```bash
# Before deployment, set DATABASE_URL
export DATABASE_URL=postgresql://user:password@localhost/bank_analyzer

# Update models.py if needed
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./statement_analyzer.db")
```

## Security Considerations

### CORS Configuration

Update `main.py` for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

### Rate Limiting

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/upload")
@limiter.limit("10/minute")
async def upload_statement(request: Request, ...):
    ...
```

### HTTPS/SSL

```bash
# For Let's Encrypt on Linux
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your-domain.com
```

## Monitoring & Logging

### Logging Setup

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.post("/upload")
async def upload_statement(...):
    logger.info(f"File uploaded: {file.filename}")
    ...
```

### Application Monitoring

Services to consider:
- **Sentry** - Error tracking
- **New Relic** - APM monitoring
- **DataDog** - Metrics & logs
- **CloudWatch** - AWS native monitoring

```python
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
```

## Database Backups

### Automated PostgreSQL Backups

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
pg_dump $DATABASE_URL > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +30 -delete
```

Schedule with cron:
```bash
0 2 * * * /scripts/backup.sh  # Daily at 2 AM
```

## Performance Optimization

### Backend
- Add caching for category lists
- Implement pagination for large datasets
- Use database indexes on session_id, date
- Compress responses with gzip

### Frontend
- Image optimization
- Code splitting
- Cache static assets
- CDN for distribution

## Scaling Considerations

### When to Upgrade
- SQLite → PostgreSQL (at ~100MB DB size)
- Single server → Multiple servers (at significant traffic)
- Add caching layer (Redis) for frequently accessed data
- Implement worker queue for large exports

## Support & Troubleshooting

### Common Issues

**Database Connection Error**
```python
# Check connection string format
postgresql://user:password@host:port/dbname
```

**Memory Limits**
- Increase on server
- Implement streaming for large exports

**Upload Timeouts**
- Increase nginx timeout: `client_body_timeout 300s;`
- Increase gunicorn timeout: `--timeout 300`

## Rollback Plan

```bash
# Keep previous versions tagged
git tag v1.0.0
git push origin v1.0.0

# Quick rollback
git checkout v1.0.0
# Redeploy
```

## Post-Launch Monitoring

1. Monitor error rates daily
2. Check database size weekly
3. Review user feedback
4. Analyze usage patterns
5. Plan feature enhancements
