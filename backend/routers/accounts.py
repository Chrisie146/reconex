"""
Chart-of-Accounts routes.

Endpoints for managing the per-client Chart of Accounts:
  - GET    /accounts                            flat list (filterable)
  - GET    /accounts/tree                       nested tree
  - GET    /accounts/templates                  available seed templates
  - POST   /accounts/seed-template              idempotent re-seed
  - GET    /accounts/{id}                       single account
  - POST   /accounts                            create user-defined account
  - PATCH  /accounts/{id}                       update (system rows: limited fields)
  - DELETE /accounts/{id}                       soft delete; refuses if linked
  - POST   /accounts/{id}/reassign              move all postings to another account
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from models import Account, Client, User, get_db
from schemas import (
    AccountCreate,
    AccountNode,
    AccountResponse,
    AccountUpdate,
    SeedTemplateRequest,
)
from services import coa_service

router = APIRouter(prefix="/accounts", tags=["Chart of Accounts"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client_or_404(client_id: int, user: User, db: Session) -> Client:
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _get_account_or_404(account_id: int, user: User, db: Session) -> Account:
    """Fetch an account and verify the caller owns its client."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    # Ownership check via client
    client = db.query(Client).filter(
        Client.id == account.client_id,
        Client.user_id == user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


# Fields editable on a system (template-seeded) account. Everything else is
# locked to keep system accounts coherent with the template.
_SYSTEM_EDITABLE = {"name", "description", "cash_flow_section", "vat_treatment", "vat_rate", "is_active"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[AccountResponse])
def list_accounts(
    client_id: int = Query(...),
    postable: bool = Query(False, description="Only return leaf (postable) accounts."),
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Flat list of accounts for a client."""
    _get_client_or_404(client_id, current_user, db)
    return coa_service.list_accounts(
        client_id=client_id,
        db=db,
        postable_only=postable,
        include_inactive=include_inactive,
    )


@router.get("/tree", response_model=List[AccountNode])
def get_account_tree(
    client_id: int = Query(...),
    postable: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nested CoA tree for the chart-of-accounts UI."""
    _get_client_or_404(client_id, current_user, db)
    return coa_service.build_tree(client_id=client_id, db=db, postable_only=postable)


@router.get("/templates")
def list_templates(current_user: User = Depends(get_current_user)):
    """Discover which CoA templates are available to seed from."""
    return {"templates": coa_service.list_templates()}


@router.post("/seed-template")
def seed_template(
    payload: SeedTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Idempotently seed (or top up) a client's CoA from a template."""
    _get_client_or_404(payload.client_id, current_user, db)
    try:
        created, skipped = coa_service.seed_template_for_client(
            client_id=payload.client_id,
            template_name=payload.template_name,
            db=db,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "success": True,
        "template": payload.template_name,
        "created": created,
        "skipped": skipped,
    }


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_account_or_404(account_id, current_user, db)


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a user-defined account. System (template) accounts cannot be
    added through this endpoint — use seed-template for those."""
    _get_client_or_404(payload.client_id, current_user, db)

    # Uniqueness: (client_id, code)
    existing = db.query(Account).filter(
        Account.client_id == payload.client_id,
        Account.code == payload.code,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Account code {payload.code} already exists for this client")

    parent = None
    level = 0
    path = ""
    if payload.parent_id is not None:
        parent = db.query(Account).filter(
            Account.id == payload.parent_id,
            Account.client_id == payload.client_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="parent_id does not belong to this client")
        level = (parent.level or 0) + 1
        path = f"{parent.path}/{parent.id}" if parent.path else f"{parent.id}"

    account = Account(
        client_id=payload.client_id,
        code=payload.code,
        name=payload.name,
        parent_id=payload.parent_id,
        path=path,
        level=level,
        account_type=payload.account_type,
        account_subtype=payload.account_subtype,
        normal_balance=payload.normal_balance,
        cash_flow_section=payload.cash_flow_section,
        is_vat_control=payload.is_vat_control,
        vat_treatment=payload.vat_treatment,
        vat_rate=payload.vat_rate,
        is_postable=payload.is_postable,
        is_active=True,
        is_system=False,
        description=payload.description,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = _get_account_or_404(account_id, current_user, db)
    changes = payload.model_dump(exclude_unset=True)

    if account.is_system:
        # System rows are locked except for the curated whitelist.
        for field in list(changes.keys()):
            if field not in _SYSTEM_EDITABLE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Field '{field}' cannot be modified on a system account",
                )

    # parent_id changes (user accounts only) need path/level recomputation.
    if "parent_id" in changes and not account.is_system:
        new_parent_id = changes["parent_id"]
        if new_parent_id == account.id:
            raise HTTPException(status_code=400, detail="Account cannot be its own parent")
        if new_parent_id is None:
            account.parent_id = None
            account.level = 0
            account.path = ""
        else:
            parent = db.query(Account).filter(
                Account.id == new_parent_id,
                Account.client_id == account.client_id,
            ).first()
            if not parent:
                raise HTTPException(status_code=400, detail="parent_id does not belong to this client")
            if parent.path and str(account.id) in parent.path.split("/"):
                raise HTTPException(status_code=400, detail="Cycle detected: cannot make a descendant a parent")
            account.parent_id = new_parent_id
            account.level = (parent.level or 0) + 1
            account.path = f"{parent.path}/{parent.id}" if parent.path else f"{parent.id}"
        changes.pop("parent_id")

    for field, value in changes.items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_account(
    account_id: int,
    force: bool = Query(False, description="If True and the account has no transactions, hard-delete the row."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete an account (sets is_active=False).

    If the account is referenced by any Transaction or learned rule, returns
    409 Conflict — caller must `POST /accounts/{id}/reassign?target_account_id=`
    first.
    """
    account = _get_account_or_404(account_id, current_user, db)

    if coa_service.has_transactions(account.id, db):
        raise HTTPException(
            status_code=409,
            detail=(
                "Account has transactions or learned rules linked to it. "
                "Reassign them first via POST /accounts/{id}/reassign."
            ),
        )

    # Block deletion of header accounts that still have active children.
    has_children = db.query(Account.id).filter(
        Account.parent_id == account.id,
        Account.is_active == True,  # noqa: E712
    ).first() is not None
    if has_children:
        raise HTTPException(status_code=409, detail="Account has active child accounts. Remove or reassign them first.")

    if force and not account.is_system:
        db.delete(account)
        db.commit()
        return {"success": True, "deleted": True, "account_id": account_id}

    account.is_active = False
    db.commit()
    return {"success": True, "deleted": False, "soft_deleted": True, "account_id": account_id}


@router.post("/{account_id}/reassign")
def reassign_account_postings(
    account_id: int,
    target_account_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reassign every Transaction (and learned rule) on this account to another."""
    src = _get_account_or_404(account_id, current_user, db)
    tgt = _get_account_or_404(target_account_id, current_user, db)
    if src.client_id != tgt.client_id:
        raise HTTPException(status_code=400, detail="Source and target accounts must belong to the same client")
    if src.id == tgt.id:
        raise HTTPException(status_code=400, detail="Source and target account must differ")
    try:
        coa_service.validate_account_for_posting(tgt.id, tgt.client_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    moved = coa_service.reassign_transactions(src.id, tgt.id, db)
    return {"success": True, "moved": moved, "from": src.id, "to": tgt.id}
