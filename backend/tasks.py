"""
Celery Background Tasks for Async Processing

Implements background tasks for:
- PDF parsing and transaction extraction
- Bulk categorization of transactions
- Report generation (Excel exports)
- Invoice metadata extraction
- Cleanup operations
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from celery import Task
from celery_app import celery_app
from sqlalchemy.orm import Session

# Import models and services (will be imported when task runs)
def get_db_session():
    """Create database session for tasks"""
    from models import SessionLocal
    return SessionLocal()


def update_task_status(db: Session, task_id: str, status: str, 
                       progress_percent: int = None, 
                       progress_message: str = None,
                       result: dict = None,
                       error_message: str = None):
    """
    Update task status in database for progress tracking
    
    Args:
        db: Database session
        task_id: Celery task ID
        status: Task status (PENDING, PROCESSING, SUCCESS, FAILED)
        progress_percent: Progress percentage (0-100)
        progress_message: Current operation message
        result: Result dictionary (will be JSON encoded)
        error_message: Error message on failure
    """
    from models import TaskStatus
    
    task_status = db.query(TaskStatus).filter(TaskStatus.task_id == task_id).first()
    
    if task_status:
        task_status.status = status
        if progress_percent is not None:
            task_status.progress_percent = progress_percent
        if progress_message is not None:
            task_status.progress_message = progress_message
        if result is not None:
            task_status.result = json.dumps(result)
        if error_message is not None:
            task_status.error_message = error_message
        task_status.updated_at = datetime.utcnow()
    
    db.commit()


@celery_app.task(bind=True, name='tasks.parse_pdf_async')
def parse_pdf_async(self: Task, pdf_content_base64: str, filename: str, 
                    user_id: int, client_id: Optional[int] = None) -> dict:
    """
    Parse PDF asynchronously and extract transactions
    
    Args:
        pdf_content_base64: Base64 encoded PDF content
        filename: Original filename
        user_id: User ID who uploaded the file
        client_id: Optional client ID for multi-tenant
        
    Returns:
        dict: {
            'session_id': str,
            'transaction_count': int,
            'bank_source': str,
            'warnings': list,
            'status': 'success' | 'error'
        }
    """
    db = None
    try:
        db = get_db_session()
        
        # Update task state to processing
        update_task_status(db, self.request.id, 'PROCESSING', 0, 'Parsing PDF...')
        
        # Decode PDF content
        import base64
        pdf_bytes = base64.b64decode(pdf_content_base64)
        
        # Parse PDF
        from services.pdf_parser import pdf_to_csv_bytes
        from services.parser import normalize_csv, validate_csv
        
        update_task_status(db, self.request.id, 'PROCESSING', 25, 'Converting PDF to CSV...')
        
        csv_bytes = pdf_to_csv_bytes(pdf_bytes, filename)
        
        # Validate CSV
        is_valid, error_msg = validate_csv(csv_bytes)
        if not is_valid:
            error_result = {'status': 'error', 'error': f'Invalid CSV: {error_msg}'}
            update_task_status(db, self.request.id, 'FAILED', 100, error_message=error_msg)
            return error_result
        
        update_task_status(db, self.request.id, 'PROCESSING', 50, 'Normalizing transactions...')
        
        # Normalize transactions
        normalized_transactions, parse_warnings, skipped_rows, bank_source = normalize_csv(csv_bytes)
        
        if not normalized_transactions:
            error_result = {'status': 'error', 'error': 'No valid transactions found in file'}
            update_task_status(db, self.request.id, 'FAILED', 100, error_message='No valid transactions found')
            return error_result
        
        update_task_status(db, self.request.id, 'PROCESSING', 75, f'Saving {len(normalized_transactions)} transactions...')
        
        # Create session ID
        session_id = str(uuid.uuid4())
        
        # Save transactions to database
        from models import Transaction, SessionState
        from services.categoriser import categorize_transaction, extract_merchant
        
        for idx, txn in enumerate(normalized_transactions):
            transaction = Transaction(
                session_id=session_id,
                client_id=client_id,
                date=txn['date'],
                description=txn['description'],
                amount=txn['amount'],
                balance=txn.get('balance'),
                category=categorize_transaction(txn['description'], txn['amount']),
                merchant=extract_merchant(txn['description'])
            )
            db.add(transaction)
        
        # Save session state
        session_state = SessionState(
            session_id=session_id,
            user_id=user_id,
            filename=filename,
            bank_source=bank_source,
            transaction_count=len(normalized_transactions),
            upload_date=datetime.utcnow()
        )
        db.add(session_state)
        
        db.commit()
        
        result = {
            'status': 'success',
            'session_id': session_id,
            'transaction_count': len(normalized_transactions),
            'bank_source': bank_source,
            'warnings': parse_warnings or [],
            'skipped_rows': skipped_rows or []
        }
        
        update_task_status(db, self.request.id, 'SUCCESS', 100, 'Completed', result=result)
        
        return result
        
    except Exception as e:
        if db:
            db.rollback()
            update_task_status(db, self.request.id, 'FAILED', 0, error_message=str(e))
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
        
    finally:
        if db:
            db.close()


@celery_app.task(bind=True, name='tasks.bulk_categorize_async')
def bulk_categorize_async(self: Task, session_id: str, user_id: int, 
                          rules: Optional[List[dict]] = None) -> dict:
    """
    Apply bulk categorization to all transactions in a session
    
    Args:
        session_id: Session ID containing transactions
        user_id: User ID for authorization
        rules: Optional list of categorization rules to apply
        
    Returns:
        dict: {
            'categorized_count': int,
            'status': 'success' | 'error'
        }
    """
    db = None
    try:
        db = get_db_session()
        
        # Get all transactions for session
        from models import Transaction
        transactions = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        total_txns = len(transactions)
        categorized_count = 0
        
        update_task_status(db, self.request.id, 'PROCESSING', 0, f'Starting categorization of {total_txns} transactions...')
        
        # Apply categorization
        from services.bulk_categorizer import BulkCategorizer
        categorizer = BulkCategorizer()
        
        for idx, txn in enumerate(transactions):
            # Update progress every 10 transactions or at the end
            if idx % 10 == 0 or idx == total_txns - 1:
                progress = int((idx + 1) / total_txns * 100)
                update_task_status(db, self.request.id, 'PROCESSING', progress, 
                                 f'Categorizing transaction {idx + 1}/{total_txns}...')
            
            # Apply categorization
            if rules:
                # Apply custom rules
                for rule in rules:
                    if categorizer.matches_rule(txn, rule):
                        txn.category = rule['category']
                        categorized_count += 1
                        break
            else:
                # Use default categorization
                from services.categoriser import categorize_transaction
                new_category = categorize_transaction(txn.description, txn.amount)
                if new_category != txn.category:
                    txn.category = new_category
                    categorized_count += 1
        
        db.commit()
        
        result = {
            'status': 'success',
            'categorized_count': categorized_count,
            'total_transactions': total_txns
        }
        
        update_task_status(db, self.request.id, 'SUCCESS', 100, 'Completed', result=result)
        
        return result
        
    except Exception as e:
        if db:
            db.rollback()
            update_task_status(db, self.request.id, 'FAILED', 0, error_message=str(e))
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
        
    finally:
        if db:
            db.close()


@celery_app.task(bind=True, name='tasks.generate_report_async')
def generate_report_async(self: Task, session_id: str, user_id: int, 
                          report_type: str = 'excel',
                          include_vat: bool = False) -> dict:
    """
    Generate report asynchronously and store result
    
    Args:
        session_id: Session ID for transactions
        user_id: User ID for authorization
        report_type: Type of report ('excel', 'pdf', 'csv')
        include_vat: Whether to include VAT calculations
        
    Returns:
        dict: {
            'file_key': str,  # Cloud storage key
            'file_size': int,
            'status': 'success' | 'error'
        }
    """
    db = None
    try:
        db = get_db_session()
        
        update_task_status(db, self.request.id, 'PROCESSING', 0, 'Fetching transactions...')
        
        # Get transactions
        from models import Transaction
        transactions = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        if not transactions:
            error_result = {'status': 'error', 'error': 'No transactions found for session'}
            update_task_status(db, self.request.id, 'FAILED', 100, error_message='No transactions found')
            return error_result
        
        update_task_status(db, self.request.id, 'PROCESSING', 25, 'Generating report...')
        
        # Generate report based on type
        if report_type == 'excel':
            from services.summary import ExcelExporter
            exporter = ExcelExporter()
            
            # Convert to dict format
            txn_dicts = [{
                'date': t.date.isoformat() if t.date else None,
                'description': t.description,
                'amount': t.amount,
                'category': t.category or '',
                'merchant': t.merchant or '',
                'vat_amount': t.vat_amount if include_vat else None,
            } for t in transactions]
            
            report_bytes = exporter.export_to_excel(txn_dicts)
            filename = f"report_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
        else:
            error_result = {'status': 'error', 'error': f'Unsupported report type: {report_type}'}
            update_task_status(db, self.request.id, 'FAILED', 100, error_message=f'Unsupported report type: {report_type}')
            return error_result
        
        update_task_status(db, self.request.id, 'PROCESSING', 75, 'Uploading report to cloud storage...')
        
        # Upload to cloud storage
        from services.storage import get_storage
        storage = get_storage()
        file_key = f"reports/{session_id}/{filename}"
        storage.upload_file(report_bytes, file_key, content_type)
        
        # Log file access
        from models import FileAccessLog
        log_entry = FileAccessLog(
            user_id=user_id,
            file_key=file_key,
            action='generate_report',
            storage_backend=os.getenv('STORAGE_BACKEND', 'local'),
            created_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        
        result = {
            'status': 'success',
            'file_key': file_key,
            'file_size': len(report_bytes),
            'filename': filename
        }
        
        update_task_status(db, self.request.id, 'SUCCESS', 100, 'Completed', result=result)
        
        return result
        
    except Exception as e:
        if db:
            db.rollback()
            update_task_status(db, self.request.id, 'FAILED', 0, error_message=str(e))
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
        
    finally:
        if db:
            db.close()


@celery_app.task(name='tasks.extract_invoice_metadata_async')
def extract_invoice_metadata_async(pdf_content_base64: str, filename: str) -> dict:
    """
    Extract invoice metadata from PDF asynchronously
    
    Args:
        pdf_content_base64: Base64 encoded PDF content
        filename: Original filename
        
    Returns:
        dict: Extracted metadata (supplier_name, invoice_date, total_amount, etc.)
    """
    try:
        import base64
        pdf_bytes = base64.b64decode(pdf_content_base64)
        
        from services.invoice_parser import extract_invoice_metadata
        metadata = extract_invoice_metadata(pdf_bytes)
        
        return {
            'status': 'success',
            'metadata': metadata
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


@celery_app.task(name='tasks.cleanup_old_results')
def cleanup_old_results():
    """
    Periodic task to clean up old Celery results and temporary files
    Runs daily at 2 AM (configured in celery_app.py beat_schedule)
    """
    try:
        # Clean up results older than 24 hours
        from celery.result import AsyncResult
        
        # This is handled automatically by result_expires setting
        # But we can add custom cleanup logic here if needed
        
        # Example: Clean up old temp files
        import glob
        temp_pattern = os.path.join(os.path.dirname(__file__), 'temp', '*.tmp')
        for temp_file in glob.glob(temp_pattern):
            try:
                file_age = datetime.utcnow() - datetime.fromtimestamp(os.path.getmtime(temp_file))
                if file_age > timedelta(days=1):
                    os.remove(temp_file)
            except Exception:
                pass
        
        return {'status': 'success', 'message': 'Cleanup completed'}
        
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
