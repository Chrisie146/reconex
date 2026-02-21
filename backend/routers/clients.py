"""
Client management routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from models import (
    Client,
    Invoice,
    OverallReconciliation,
    Reconciliation,
    Rule,
    Transaction,
    User,
    get_db,
)
from routers.dependencies import logger

router = APIRouter(tags=["Clients"])


@router.get("/clients")
def get_clients(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all clients for authenticated user with statistics"""
    try:
        clients = db.query(Client).filter(Client.user_id == current_user.id).all()

        result = []
        for c in clients:
            statement_count = (
                db.query(func.count(func.distinct(Transaction.session_id)))
                .filter(Transaction.client_id == c.id)
                .scalar()
                or 0
            )
            transaction_count = (
                db.query(func.count(Transaction.id)).filter(Transaction.client_id == c.id).scalar() or 0
            )
            last_date = db.query(func.max(Transaction.date)).filter(Transaction.client_id == c.id).scalar()

            result.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "created_at": c.created_at.isoformat(),
                    "statement_count": statement_count,
                    "transaction_count": transaction_count,
                    "last_statement_date": last_date.isoformat() if last_date else None,
                }
            )

        return {"clients": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch clients: {str(e)}")


@router.post("/clients")
def create_client(
    name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new client for authenticated user"""
    try:
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Client name is required")

        client = Client(user_id=current_user.id, name=name.strip())
        db.add(client)
        db.commit()
        db.refresh(client)

        return {
            "client": {
                "id": client.id,
                "name": client.name,
                "created_at": client.created_at.isoformat(),
                "statement_count": 0,
                "transaction_count": 0,
                "last_statement_date": None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create client: {str(e)}")


@router.put("/clients/{client_id}")
def update_client(
    client_id: int,
    name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a client's name (authenticated user only)"""
    try:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="Client name is required")

        client.name = name.strip()
        db.commit()
        db.refresh(client)

        return {"id": client.id, "name": client.name, "created_at": client.created_at.isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update client: {str(e)}")


@router.delete("/clients/{client_id}")
def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a client and all associated data (authenticated user only)"""
    try:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        db.query(Transaction).filter(Transaction.client_id == client_id).delete()
        db.query(Rule).filter(Rule.client_id == client_id).delete()
        db.query(Invoice).filter(Invoice.client_id == client_id).delete()
        db.query(Reconciliation).filter(Reconciliation.client_id == client_id).delete()
        db.query(OverallReconciliation).filter(OverallReconciliation.client_id == client_id).delete()
        db.query(Client).filter(Client.id == client_id).delete()
        db.commit()

        return {"message": "Client deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete client: {str(e)}")
