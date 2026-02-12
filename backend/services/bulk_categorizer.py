"""
Bulk Transaction Categorization Service
Handles safe, reversible bulk category updates with undo capability
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multilingual


@dataclass
class BulkAction:
    """Represents a bulk categorization action for undo purposes"""
    action_id: str
    keyword: str
    category: str
    timestamp: str
    matched_transactions: List[Dict[str, Any]]  # Store original state
    transaction_ids: List[int]
    
    def to_dict(self) -> Dict:
        return asdict(self)


class BulkCategorizer:
    """
    Manages bulk transaction categorization with undo capability
    Stores one-level undo in memory (per session)
    """
    
    def __init__(self):
        self.last_action: Optional[BulkAction] = None
        self.action_count = 0
    
    def validate_rule(self, keyword: str, category: str) -> Tuple[bool, str]:
        """
        Validate bulk categorization rule
        
        Returns:
            (is_valid, error_message)
        """
        if not keyword or not keyword.strip():
            return False, "Keyword cannot be empty"
        
        if len(keyword.strip()) < 3:
            return False, "Keyword must be at least 3 characters"
        
        if not category or not category.strip():
            return False, "Category cannot be empty"
        
        return True, ""
    
    def find_matching_transactions(
        self,
        transactions: List[Dict[str, Any]],
        keyword: str,
        only_uncategorised: bool = True
    ) -> List[int]:
        """
        Find transaction IDs matching keyword in description
        
        Args:
            transactions: List of transaction dicts with 'id', 'description', 'category'
            keyword: Search keyword (case-insensitive, substring match)
            only_uncategorised: If True, only match uncategorised transactions
        
        Returns:
            List of matching transaction IDs
        """
        # For deterministic matching use the project's multilingual helper.
        # Do not translate; match keyword against description only.
        keyword_norm = (keyword or "").strip()
        matching_ids = []

        # Log helpful debugging info
        print(f"\n[BULK_CATEGORIZER] Finding matches for keyword: '{keyword}' (normalized: '{keyword_norm}')")
        print(f"[BULK_CATEGORIZER] only_uncategorised: {only_uncategorised}")

        for i, txn in enumerate(transactions):
            raw_desc = txn.get("description", "") or ""
            # Normalize OCR or free text in a deterministic way
            desc_norm = multilingual.handle_ocr_text(raw_desc)
            category = txn.get("category", "") or ""
            txn_id = txn.get("id")

            is_match = False
            if keyword_norm:
                # Use the deterministic word-aware matcher first
                if multilingual.match_keyword_in_text(keyword_norm, desc_norm):
                    is_match = True
                else:
                    # fallback: allow substring/prefix matches to remain useful
                    low_keyword = keyword_norm.lower()
                    if low_keyword in desc_norm.lower():
                        is_match = True
                    else:
                        tokens = desc_norm.lower().split()
                        for t in tokens:
                            if t.startswith(low_keyword):
                                is_match = True
                                break

            if is_match:
                print(f"[BULK_CATEGORIZER] Txn {i}: ID={txn_id}, RAW='{raw_desc}', NORM='{desc_norm}', CAT='{category}', MATCHES=True")
                # Only apply if uncategorised or allowed to overwrite
                if not only_uncategorised or not category or category == "Other":
                    print(f"  -> Adding to matching list (only_uncategorised={only_uncategorised}, category='{category}')")
                    matching_ids.append(txn_id)
                else:
                    print(f"  -> Skipped (only_uncategorised is True but category='{category}')")

        print(f"[BULK_CATEGORIZER] Total matches found: {len(matching_ids)}\n")
        return matching_ids
    
    def apply_bulk_categorization(
        self,
        transactions: List[Dict[str, Any]],
        keyword: str,
        category: str,
        only_uncategorised: bool = True
    ) -> Tuple[int, List[Dict[str, Any]], str]:
        """
        Apply category to all matching transactions
        
        Args:
            transactions: List of transaction dicts
            keyword: Search keyword
            category: Category to apply
            only_uncategorised: If True, don't overwrite existing categories
        
        Returns:
            (count_updated, updated_transactions_list, error_message)
        """
        # Validate
        is_valid, error_msg = self.validate_rule(keyword, category)
        if not is_valid:
            return 0, [], error_msg
        
        # Find matching transactions
        matching_ids = self.find_matching_transactions(
            transactions,
            keyword,
            only_uncategorised
        )
        
        if not matching_ids:
            return 0, [], ""
        
        # Store original state for undo (before modification)
        original_state = []
        for txn in transactions:
            if txn.get("id") in matching_ids:
                original_state.append({
                    "id": txn.get("id"),
                    "category": txn.get("category"),
                    "description": txn.get("description")
                })
        
        # Apply new category
        updated_count = 0
        updated_transactions = []
        
        for txn in transactions:
            if txn.get("id") in matching_ids:
                txn["category"] = category
                updated_transactions.append(txn)
                updated_count += 1
        
        # Store action for undo
        import uuid
        action_id = str(uuid.uuid4())
        self.last_action = BulkAction(
            action_id=action_id,
            keyword=keyword,
            category=category,
            timestamp=datetime.utcnow().isoformat(),
            matched_transactions=original_state,
            transaction_ids=matching_ids
        )
        self.action_count += 1
        
        return updated_count, updated_transactions, ""
    
    def undo_last_action(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Undo the last bulk categorization action
        
        Args:
            transactions: Current transaction list
        
        Returns:
            (success, message, updated_transactions)
        """
        if not self.last_action:
            return False, "No undo available", transactions
        
        # Restore original categories
        for original in self.last_action.matched_transactions:
            for txn in transactions:
                if txn.get("id") == original.get("id"):
                    txn["category"] = original.get("category")

        # Capture info for message, then clear undo buffer
        action_info = {
            "keyword": self.last_action.keyword,
            "category": self.last_action.category,
        }
        self.last_action = None

        message = f"Reverted bulk categorization for '{action_info['keyword']}'"
        return True, message, transactions
    
    def get_last_action_info(self) -> Optional[Dict[str, Any]]:
        """Get info about the last action (for undo button display)"""
        if not self.last_action:
            return None
        
        return {
            "keyword": self.last_action.keyword,
            "category": self.last_action.category,
            "count": len(self.last_action.transaction_ids),
            "timestamp": self.last_action.timestamp
        }
