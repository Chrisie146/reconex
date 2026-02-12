# Background Jobs & Task Queue Guide

## Overview

The Background Jobs feature enables asynchronous processing of long-running operations using Celery distributed task queue with Redis as the message broker. This prevents API requests from timing out and provides real-time progress tracking.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│  FastAPI App    │────▶│    Redis     │◀────│ Celery Worker  │
│  (Web Server)   │     │   (Broker)   │     │  (Background)  │
└─────────────────┘     └──────────────┘     └────────────────┘
        │                       │                      │
        │                       │                      │
        ▼                       ▼                      ▼
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│   PostgreSQL    │     │    Redis     │     │   PostgreSQL   │
│ (task_status)   │     │  (Results)   │     │  (Operations)  │
└─────────────────┘     └──────────────┘     └────────────────┘
```

## Features

### Supported Async Operations

1. **PDF Parsing** - Extract transactions from PDF bank statements
2. **Bulk Categorization** - Apply categorization rules to multiple transactions
3. **Report Generation** - Generate Excel reports for large datasets

### Task Management

- **Progress Tracking** - Real-time progress updates (0-100%)
- **Status Monitoring** - Task states: PENDING, PROCESSING, SUCCESS, FAILED
- **Result Storage** - Results stored in database for 1 hour
- **Automatic Retry** - Failed tasks retry up to 3 times with exponential backoff
- **Cancellation** - Running tasks can be cancelled by user

## Setup

### 1. Install Redis Server

#### Windows (using Chocolatey)
```powershell
choco install redis-64
redis-server --service-install
redis-server --service-start
```

#### Windows (using WSL)
```bash
wsl --install
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

#### Linux
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### macOS
```bash
brew install redis
brew services start redis
```

### 2. Verify Redis Installation

```bash
redis-cli ping
# Should return: PONG
```

### 3. Install Python Dependencies

Dependencies are already in requirements.txt:
```txt
celery==5.3.4
redis==4.6.0
flower==2.0.1
```

Install them:
```bash
cd backend
pip install -r requirements.txt
```

### 4. Database Migration

The `task_status` table is required for progress tracking:

```bash
cd backend
alembic upgrade head
```

Or for development (SQLite):
```bash
python -c "from models import init_db; init_db()"
alembic stamp head
```

## Running the System

### 1. Start Redis Server

Make sure Redis is running:
```bash
redis-cli ping
```

### 2. Start Celery Worker

In a separate terminal:
```bash
cd backend
celery -A celery_app worker --loglevel=info --pool=solo
```

**Note:** Use `--pool=solo` on Windows. On Linux/macOS, you can omit it for better performance.

#### Worker Options:
- `--concurrency=4` - Number of worker processes (default: CPU count)
- `--loglevel=info` - Logging level (debug, info, warning, error)
- `--pool=solo` - Required on Windows
- `--queues=pdf_processing,bulk_operations,reports` - Specific queues to process

### 3. Start Celery Beat (Optional)

For periodic tasks (cleanup at 2 AM):
```bash
cd backend
celery -A celery_app beat --loglevel=info
```

### 4. Start Flower Monitoring (Optional)

For web-based task monitoring:
```bash
cd backend
celery -A celery_app flower
```

Access at: http://localhost:5555

### 5. Start FastAPI Application

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### 1. Upload PDF Asynchronously

**Endpoint:** `POST /upload_pdf_async`

**Request:**
```bash
curl -X POST "http://localhost:8000/upload_pdf_async" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@statement.pdf" \
  -F "client_id=1"
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "submitted",
  "message": "PDF parsing started. Use GET /tasks/{task_id}/status to check progress."
}
```

### 2. Check Task Status

**Endpoint:** `GET /tasks/{task_id}/status`

**Request:**
```bash
curl -X GET "http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (In Progress):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_name": "parse_pdf_async",
  "status": "PROCESSING",
  "progress_percent": 75,
  "progress_message": "Saving 1250 transactions...",
  "created_at": "2024-02-12T14:30:00",
  "updated_at": "2024-02-12T14:30:15"
}
```

**Response (Complete):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_name": "parse_pdf_async",
  "status": "SUCCESS",
  "progress_percent": 100,
  "progress_message": "Completed",
  "created_at": "2024-02-12T14:30:00",
  "updated_at": "2024-02-12T14:30:25"
}
```

### 3. Get Task Result

**Endpoint:** `GET /tasks/{task_id}/result`

**Request:**
```bash
curl -X GET "http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000/result" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "session_id": "abc123-def456-ghi789",
    "transaction_count": 1250,
    "bank_source": "Standard Bank",
    "warnings": [],
    "skipped_rows": []
  }
}
```

### 4. Bulk Categorize Asynchronously

**Endpoint:** `POST /bulk_categorize_async`

**Request:**
```bash
curl -X POST "http://localhost:8000/bulk_categorize_async?session_id=abc123-def456-ghi789" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rules": [
      {
        "category": "Salary",
        "conditions": {
          "field": "description",
          "op": "contains",
          "value": "SALARY"
        }
      }
    ]
  }'
```

**Response:**
```json
{
  "task_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "submitted",
  "message": "Bulk categorization started. Use GET /tasks/{task_id}/status to check progress."
}
```

### 5. Generate Report Asynchronously

**Endpoint:** `POST /reports/generate_async`

**Request:**
```bash
curl -X POST "http://localhost:8000/reports/generate_async?session_id=abc123-def456-ghi789&report_type=excel&include_vat=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "task_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "submitted",
  "message": "Report generation started. Use GET /tasks/{task_id}/status to check progress."
}
```

**Result (after completion):**
```json
{
  "status": "success",
  "file_key": "reports/abc123-def456-ghi789/report_20240212_143025.xlsx",
  "file_size": 245678,
  "filename": "report_20240212_143025.xlsx"
}
```

Then download using the file_key:
```bash
curl -X GET "http://localhost:8000/download_file?file_key=reports/abc123-def456-ghi789/report_20240212_143025.xlsx" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. Cancel Task

**Endpoint:** `DELETE /tasks/{task_id}`

**Request:**
```bash
curl -X DELETE "http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (Running Task):**
```json
{
  "message": "Task cancelled"
}
```

**Response (Completed Task):**
```json
{
  "message": "Task result deleted"
}
```

## Frontend Integration

### JavaScript Example

```javascript
// Submit PDF for async processing
async function uploadPDFAsync(file, accessToken) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/upload_pdf_async', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    },
    body: formData
  });
  
  const data = await response.json();
  return data.task_id;
}

// Poll for task status
async function pollTaskStatus(taskId, accessToken, onProgress) {
  const pollInterval = 2000; // Poll every 2 seconds
  
  while (true) {
    const response = await fetch(
      `http://localhost:8000/tasks/${taskId}/status`,
      {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      }
    );
    
    const status = await response.json();
    
    // Update UI with progress
    onProgress(status.progress_percent, status.progress_message);
    
    // Check if complete
    if (status.status === 'SUCCESS') {
      // Fetch result
      const resultResponse = await fetch(
        `http://localhost:8000/tasks/${taskId}/result`,
        {
          headers: { 'Authorization': `Bearer ${accessToken}` }
        }
      );
      return await resultResponse.json();
    }
    
    if (status.status === 'FAILED') {
      throw new Error('Task failed');
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }
}

// Usage
const taskId = await uploadPDFAsync(file, token);
const result = await pollTaskStatus(taskId, token, (percent, message) => {
  console.log(`Progress: ${percent}% - ${message}`);
  updateProgressBar(percent);
});
console.log('Task complete:', result);
```

### React Hook Example

```javascript
import { useState, useEffect } from 'react';

function useAsyncTask(taskId, accessToken) {
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!taskId) return;
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/tasks/${taskId}/status`,
          {
            headers: { 'Authorization': `Bearer ${accessToken}` }
          }
        );
        
        const data = await response.json();
        setStatus(data);
        
        if (data.status === 'SUCCESS') {
          const resultResponse = await fetch(
            `http://localhost:8000/tasks/${taskId}/result`,
            {
              headers: { 'Authorization': `Bearer ${accessToken}` }
            }
          );
          const resultData = await resultResponse.json();
          setResult(resultData.result);
          clearInterval(pollInterval);
        } else if (data.status === 'FAILED') {
          setError('Task failed');
          clearInterval(pollInterval);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(pollInterval);
      }
    }, 2000);
    
    return () => clearInterval(pollInterval);
  }, [taskId, accessToken]);
  
  return { status, result, error };
}

// Usage in component
function PDFUploadComponent() {
  const [taskId, setTaskId] = useState(null);
  const { status, result, error } = useAsyncTask(taskId, accessToken);
  
  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('http://localhost:8000/upload_pdf_async', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` },
      body: formData
    });
    
    const data = await response.json();
    setTaskId(data.task_id);
  };
  
  return (
    <div>
      {!taskId && <FileUpload onUpload={handleUpload} />}
      {status && (
        <ProgressBar 
          percent={status.progress_percent} 
          message={status.progress_message} 
        />
      )}
      {result && <ResultDisplay result={result} />}
      {error && <ErrorMessage error={error} />}
    </div>
  );
}
```

## Configuration

### Celery Settings (celery_app.py)

```python
# Task time limits
task_time_limit = 1800  # 30 minutes hard limit
task_soft_time_limit = 1500  # 25 minutes soft limit

# Result expiration
result_expires = 3600  # Results expire after 1 hour

# Retry configuration
task_max_retries = 3  # Retry failed tasks up to 3 times
task_default_retry_delay = 60  # Wait 60 seconds between retries

# Worker settings
worker_prefetch_multiplier = 4  # Prefetch 4 tasks per worker
worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks

# Beat schedule
beat_schedule = {
    'cleanup-old-results': {
        'task': 'tasks.cleanup_old_results',
        'schedule': crontab(hour=2, minute=0),  # Run at 2:00 AM daily
    }
}
```

### Task Routes

Tasks are routed to specific queues for better organization:

- `pdf_processing` - PDF parsing tasks
- `bulk_operations` - Bulk categorization tasks
- `reports` - Report generation tasks
- `default` - All other tasks

To process only specific queues:
```bash
celery -A celery_app worker --queues=pdf_processing,bulk_operations
```

## Monitoring

### Flower Dashboard

Access the Flower web interface at http://localhost:5555

Features:
- Real-time task monitoring
- Worker status and statistics
- Task history and results
- Queue monitoring
- Worker pool management

### Redis Monitoring

Check Redis status:
```bash
redis-cli info
redis-cli monitor  # Watch commands in real-time
```

### Task Statistics

```bash
# Check active tasks
redis-cli keys "celery-task-meta-*"

# Check queue lengths
redis-cli llen celery
redis-cli llen pdf_processing
redis-cli llen bulk_operations
redis-cli llen reports
```

## Troubleshooting

### Worker Not Processing Tasks

1. **Check Redis connection:**
   ```bash
   redis-cli ping
   ```

2. **Check worker logs:**
   ```bash
   celery -A celery_app worker --loglevel=debug
   ```

3. **Verify task is in queue:**
   ```bash
   redis-cli llen celery
   ```

### Tasks Failing

1. **Check worker logs** for error details
2. **Verify database connection** in worker environment
3. **Check task time limits** - increase if needed
4. **Review error message** in task status

### Redis Connection Errors

1. **Verify Redis is running:**
   ```bash
   redis-cli ping
   ```

2. **Check Redis configuration:**
   - Default: `redis://localhost:6379/0`
   - Update in celery_app.py if needed

3. **Test connection:**
   ```python
   import redis
   r = redis.Redis(host='localhost', port=6379, db=0)
   r.ping()
   ```

### Tasks Stuck in PENDING

1. **Restart Celery worker**
2. **Check task routes** - ensure worker processes correct queues
3. **Verify task exists in Redis:**
   ```bash
   redis-cli keys "celery-task-meta-*"
   ```

### High Memory Usage

1. **Reduce worker_prefetch_multiplier** (default: 4)
2. **Set worker_max_tasks_per_child** (default: 1000)
3. **Limit result_expires** (default: 3600 seconds)

## Performance Optimization

### Worker Scaling

**Horizontal Scaling:**
```bash
# Start multiple workers
celery -A celery_app worker --loglevel=info --concurrency=4 -n worker1@%h
celery -A celery_app worker --loglevel=info --concurrency=4 -n worker2@%h
```

**Vertical Scaling:**
```bash
# Increase concurrency
celery -A celery_app worker --loglevel=info --concurrency=8
```

### Queue Prioritization

Process high-priority queues first:
```bash
celery -A celery_app worker --queues=pdf_processing:10,reports:5,default:1
```

### Task Optimization

1. **Batch processing** - Group small tasks together
2. **Chunking** - Split large tasks into smaller pieces
3. **Result backend optimization** - Use Redis for fast results
4. **Progress updates** - Update every N iterations, not every iteration

## Security

### Task Authorization

All async endpoints require JWT authentication. Tasks inherit user context:

```python
@app.post("/upload_pdf_async")
async def upload_pdf_async(
    current_user: User = Depends(get_current_user)  # JWT required
):
    task = parse_pdf_async.delay(
        user_id=current_user.id  # User context preserved
    )
```

### Task Isolation

- Each user can only access their own tasks
- Task results filtered by user_id in database
- No cross-user task visibility

### Result Expiration

- Results automatically expire after 1 hour
- Periodic cleanup task runs at 2 AM daily
- Manual deletion via `DELETE /tasks/{task_id}`

## Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/opt/statement_analyzer/backend
ExecStart=/opt/statement_analyzer/venv/bin/celery -A celery_app worker \
           --loglevel=info --concurrency=8 --pidfile=/var/run/celery/worker.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl enable celery-worker
sudo systemctl start celery-worker
sudo systemctl status celery-worker
```

### Docker Deployment

```dockerfile
# Dockerfile.worker
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

CMD ["celery", "-A", "backend.celery_app", "worker", "--loglevel=info"]
```

docker-compose.yml:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
    deploy:
      replicas: 3
  
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.worker
    depends_on:
      - redis
    command: celery -A backend.celery_app beat --loglevel=info
  
  flower:
    build:
      context: .
      dockerfile: Dockerfile.worker
    depends_on:
      - redis
    command: celery -A backend.celery_app flower
    ports:
      - "5555:5555"
```

## Testing

### Manual Testing

1. Start all services (Redis, Celery, FastAPI)
2. Upload a PDF asynchronously
3. Poll task status every 2 seconds
4. Verify progress updates
5. Retrieve final result

### Automated Testing

```python
import pytest
from celery import Celery
from tasks import parse_pdf_async

@pytest.fixture
def celery_app():
    app = Celery('tasks')
    app.conf.update(
        broker_url='redis://localhost:6379/1',  # Test database
        result_backend='redis://localhost:6379/1',
        task_always_eager=True,  # Execute tasks synchronously for testing
        task_eager_propagates=True
    )
    return app

def test_parse_pdf_async(celery_app, sample_pdf_base64):
    result = parse_pdf_async.apply(
        args=[sample_pdf_base64, 'test.pdf', 1, None]
    )
    
    assert result.successful()
    assert result.result['status'] == 'success'
    assert result.result['transaction_count'] > 0
```

## Best Practices

1. **Always use async for long operations** (> 5 seconds)
2. **Implement proper error handling** with retry logic
3. **Update progress regularly** for better UX
4. **Set reasonable timeouts** (30 min default)
5. **Clean up old results** to save storage
6. **Monitor worker health** with Flower
7. **Scale workers based on load** (horizontal scaling)
8. **Use specific queues** for different task types
9. **Log task failures** for debugging
10. **Test with realistic data** before production

## Additional Resources

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/documentation)
- [Flower Documentation](https://flower.readthedocs.io/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

## Support

For issues or questions:
1. Check worker logs
2. Review Flower dashboard
3. Test Redis connection
4. Verify database migrations
5. Check API endpoint responses

---

**Status:** ✅ Background Jobs feature is production-ready
**Version:** 1.0.0
**Last Updated:** February 12, 2026
