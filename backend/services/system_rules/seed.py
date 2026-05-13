"""
Idempotent seeder for system_rules. Run on app startup.

Reads the curated JSON pack(s) in this directory and upserts each rule by
`code`. New rules are inserted; existing rules are updated in place (so a
pack revision automatically rolls out on restart). Disabled rules in the
pack are honoured; rules removed from the pack are not auto-deleted —
operators flip `enabled=false` instead, to preserve audit history.
"""

import json
import logging
import os
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from models import SystemRule

logger = logging.getLogger(__name__)

PACK_DIR = os.path.dirname(__file__)
DEFAULT_PACKS = ["sa_pack_v1"]


def _load_pack(pack_name: str) -> List[Dict[str, Any]]:
    path = os.path.join(PACK_DIR, f"{pack_name}.json")
    if not os.path.exists(path):
        logger.warning("System rules pack not found: %s", path)
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("rules", [])


def seed_system_rules(db: Session, packs: List[str] = None) -> Dict[str, int]:
    """Upsert all rules from the given packs (or DEFAULT_PACKS).

    Returns counts for visibility: ``{"inserted": n, "updated": m, "unchanged": k}``.
    """
    packs = packs or DEFAULT_PACKS
    inserted = updated = unchanged = 0

    for pack_name in packs:
        for entry in _load_pack(pack_name):
            code = entry.get("code")
            if not code:
                continue
            conditions_json = json.dumps(entry.get("conditions", {}))
            entity_filter = entry.get("entity_filter")
            entity_filter_json = json.dumps(entity_filter) if entity_filter else None

            existing = db.query(SystemRule).filter(SystemRule.code == code).first()
            if existing is None:
                db.add(SystemRule(
                    code=code,
                    name=entry["name"],
                    priority=entry.get("priority", 100),
                    conditions=conditions_json,
                    purpose=entry["purpose"],
                    coa_hint=entry.get("coa_hint"),
                    confidence=entry.get("confidence", "medium"),
                    entity_filter=entity_filter_json,
                    description=entry.get("description"),
                    enabled=entry.get("enabled", True),
                ))
                inserted += 1
                continue

            changed = False
            for field, new_val in (
                ("name", entry["name"]),
                ("priority", entry.get("priority", 100)),
                ("conditions", conditions_json),
                ("purpose", entry["purpose"]),
                ("coa_hint", entry.get("coa_hint")),
                ("confidence", entry.get("confidence", "medium")),
                ("entity_filter", entity_filter_json),
                ("description", entry.get("description")),
                ("enabled", entry.get("enabled", True)),
            ):
                if getattr(existing, field) != new_val:
                    setattr(existing, field, new_val)
                    changed = True
            if changed:
                updated += 1
            else:
                unchanged += 1

    db.commit()
    logger.info(
        "System rules seeded — inserted=%s updated=%s unchanged=%s",
        inserted, updated, unchanged,
    )
    return {"inserted": inserted, "updated": updated, "unchanged": unchanged}
