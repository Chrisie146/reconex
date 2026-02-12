"""
Celery Configuration for Background Task Processing

Configures Celery with Redis as message broker and result backend.
Supports async PDF parsing, bulk operations, and scheduled tasks.
"""

import os
from celery import Celery
from celery.schedules import crontab
from config import Config

# Create Celery app
celery_app = Celery(
    'bank_statement_analyzer',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker crashes
    
    # Result backend settings  
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional task metadata
    
    # Retry settings
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,  # Maximum 3 retry attempts
    
    # Worker settings
    worker_prefetch_multiplier=4,  # Number of tasks to prefetch
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Beat scheduler (for periodic tasks)
    beat_schedule={
        # Example: Clean up old results every day at 2 AM
        'cleanup-old-results': {
            'task': 'tasks.cleanup_old_results',
            'schedule': crontab(hour=2, minute=0),
        },
        # Example: Generate daily reports at 6 AM
        # 'generate-daily-reports': {
        #     'task': 'tasks.generate_daily_reports',
        #     'schedule': crontab(hour=6, minute=0),
        # },
    },
)

# Auto-discover tasks from tasks.py module
celery_app.autodiscover_tasks(['backend'], force=True)

# Task routes (optional: route specific tasks to specific queues)
celery_app.conf.task_routes = {
    'tasks.parse_pdf_async': {'queue': 'pdf_processing'},
    'tasks.bulk_categorize_async': {'queue': 'bulk_operations'},
    'tasks.generate_report_async': {'queue': 'reports'},
    'tasks.*': {'queue': 'default'},
}

if __name__ == '__main__':
    celery_app.start()
