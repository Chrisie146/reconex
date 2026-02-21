"""
Background jobs routes: async upload, async categorize, async report, task CRUD.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from models import SessionState, User, get_db
from rate_limiter import upload_limiter
from validators import validate_pdf_upload

router = APIRouter(tags=["Background Jobs"])


@router.post("/upload_pdf_async")
async def upload_pdf_async(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None,
):
    """Upload PDF asynchronously and return task ID for progress tracking."""
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)
    await validate_pdf_upload(file)

    try:
        content = await file.read()

        import base64

        content_base64 = base64.b64encode(content).decode("utf-8")

        from tasks import parse_pdf_async

        task = parse_pdf_async.delay(
            pdf_content_base64=content_base64,
            filename=file.filename,
            user_id=current_user.id,
            client_id=client_id,
        )

        from models import TaskStatus

        task_status = TaskStatus(
            task_id=task.id,
            user_id=current_user.id,
            task_name="parse_pdf_async",
            status="PENDING",
            progress_percent=0,
            progress_message="Task submitted",
        )
        db.add(task_status)
        db.commit()

        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "PDF parsing started. Use GET /tasks/{task_id}/status to check progress.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit task: {str(e)}")


@router.post("/bulk_categorize_async")
async def bulk_categorize_async_endpoint(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rules: Optional[List[dict]] = None,
):
    """Apply bulk categorization asynchronously."""
    try:
        session_state = db.query(SessionState).filter(
            SessionState.session_id == session_id,
            SessionState.user_id == current_user.id,
        ).first()
        if not session_state:
            raise HTTPException(status_code=404, detail="Session not found")

        from tasks import bulk_categorize_async

        task = bulk_categorize_async.delay(session_id=session_id, user_id=current_user.id, rules=rules)

        from models import TaskStatus

        task_status = TaskStatus(
            task_id=task.id,
            user_id=current_user.id,
            task_name="bulk_categorize_async",
            status="PENDING",
            progress_percent=0,
            progress_message="Task submitted",
        )
        db.add(task_status)
        db.commit()

        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "Bulk categorization started. Use GET /tasks/{task_id}/status to check progress.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit task: {str(e)}")


@router.post("/reports/generate_async")
async def generate_report_async_endpoint(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    report_type: str = "excel",
    include_vat: bool = False,
):
    """Generate report asynchronously in background."""
    try:
        session_state = db.query(SessionState).filter(
            SessionState.session_id == session_id,
            SessionState.user_id == current_user.id,
        ).first()
        if not session_state:
            raise HTTPException(status_code=404, detail="Session not found")

        from tasks import generate_report_async

        task = generate_report_async.delay(
            session_id=session_id,
            user_id=current_user.id,
            report_type=report_type,
            include_vat=include_vat,
        )

        from models import TaskStatus

        task_status = TaskStatus(
            task_id=task.id,
            user_id=current_user.id,
            task_name="generate_report_async",
            status="PENDING",
            progress_percent=0,
            progress_message="Task submitted",
        )
        db.add(task_status)
        db.commit()

        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "Report generation started. Use GET /tasks/{task_id}/status to check progress.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to submit task: {str(e)}")


@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status and progress of a background task."""
    from models import TaskStatus

    task_status = db.query(TaskStatus).filter(
        TaskStatus.task_id == task_id,
        TaskStatus.user_id == current_user.id,
    ).first()
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_status.task_id,
        "task_name": task_status.task_name,
        "status": task_status.status,
        "progress_percent": task_status.progress_percent,
        "progress_message": task_status.progress_message,
        "created_at": task_status.created_at.isoformat(),
        "updated_at": task_status.updated_at.isoformat(),
    }


@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get result of a completed background task."""
    from models import TaskStatus

    task_status = db.query(TaskStatus).filter(
        TaskStatus.task_id == task_id,
        TaskStatus.user_id == current_user.id,
    ).first()
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_status.status != "SUCCESS":
        return {
            "task_id": task_id,
            "status": task_status.status,
            "message": "Task not completed yet"
            if task_status.status in ["PENDING", "PROCESSING"]
            else f"Task failed: {task_status.error_message}",
        }

    result_data = json.loads(task_status.result) if task_status.result else {}
    return {"task_id": task_id, "status": "SUCCESS", "result": result_data}


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a running task or delete task result."""
    from models import TaskStatus
    from celery.result import AsyncResult

    task_status = db.query(TaskStatus).filter(
        TaskStatus.task_id == task_id,
        TaskStatus.user_id == current_user.id,
    ).first()
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_status.status in ["PENDING", "PROCESSING"]:
        celery_task = AsyncResult(task_id)
        celery_task.revoke(terminate=True)
        task_status.status = "CANCELLED"
        task_status.error_message = "Cancelled by user"
        db.commit()
        return {"message": "Task cancelled"}
    else:
        db.delete(task_status)
        db.commit()
        return {"message": "Task result deleted"}
