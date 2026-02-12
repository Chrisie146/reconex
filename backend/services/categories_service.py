"""
Categories and Rules Management Service
Handles category CRUD, rule creation/management, and rule-based categorization
with multilingual keyword support and priority-based matching.
"""

import sys
import os
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multilingual
from sqlalchemy.orm import Session
from models import CustomCategory, SessionLocal


# Built-in categories that are always available
BUILT_IN_CATEGORIES = [
    "Fuel",
    "Bank Fees",
    "Rent",
    "Salary",
    "Groceries",
    "Utilities",
    "Transport",
    "Healthcare",
    "Insurance",
    "Entertainment",
    "Clothing",
    "Dining",
    "Travel",
    "Education",
    "Other"
]

# Built-in category VAT defaults (South African context)
BUILT_IN_CATEGORY_VAT_DEFAULTS = {
    "Fuel": {"applicable": True, "rate": 15.0},
    "Bank Fees": {"applicable": False, "rate": 0.0},
    "Rent": {"applicable": False, "rate": 0.0},
    "Salary": {"applicable": False, "rate": 0.0},
    "Groceries": {"applicable": True, "rate": 15.0},
    "Utilities": {"applicable": True, "rate": 15.0},
    "Transport": {"applicable": True, "rate": 15.0},
    "Healthcare": {"applicable": False, "rate": 0.0},
    "Insurance": {"applicable": False, "rate": 0.0},
    "Entertainment": {"applicable": True, "rate": 15.0},
    "Clothing": {"applicable": True, "rate": 15.0},
    "Dining": {"applicable": True, "rate": 15.0},
    "Travel": {"applicable": True, "rate": 15.0},
    "Education": {"applicable": False, "rate": 0.0},
    "Other": {"applicable": False, "rate": 0.0},
}


@dataclass
class CategoryRule:
    """Represents a categorization rule with keywords and priority"""
    rule_id: str
    name: str
    category: str
    keywords: List[str]  # Can be in English or Afrikaans
    priority: int  # Lower number = higher priority (0 is highest)
    auto_apply: bool  # If True, apply automatically; if False, require approval
    enabled: bool
    match_compound_words: bool = False  # If True, match keywords in compound words like "RenteOpDTBal"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CategoriesService:
    """Service for managing categories and rules"""
    
    def __init__(self):
        # Session-scoped storage: session_id -> rules list
        self.session_rules: Dict[str, List[CategoryRule]] = {}
        # Note: Custom categories are now stored in the database, not in memory
    
    def _get_db(self) -> Session:
        """Get a database session"""
        return SessionLocal()
    
    def get_all_categories(self, session_id: Optional[str] = None) -> List[str]:
        """Get all available categories (built-in + custom from database)"""
        categories = list(BUILT_IN_CATEGORIES)
        
        # Load custom categories from database
        db = self._get_db()
        try:
            custom_cats = db.query(CustomCategory).all()
            categories.extend([cat.name for cat in custom_cats])
        finally:
            db.close()
        
        return sorted(list(set(categories)))
    
    def get_all_categories_with_vat(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all available categories with VAT settings"""
        categories = []
        custom_category_names = set()
        
        # Load custom categories from database
        db = self._get_db()
        try:
            custom_cats = db.query(CustomCategory).all()
            for cat in custom_cats:
                categories.append({
                    "name": cat.name,
                    "is_built_in": cat.name in BUILT_IN_CATEGORIES,  # Mark if this is an override of a built-in
                    "vat_applicable": cat.vat_applicable == 1,
                    "vat_rate": cat.vat_rate
                })
                custom_category_names.add(cat.name)
        finally:
            db.close()
        
        # Add built-in categories that haven't been overridden
        for cat_name in BUILT_IN_CATEGORIES:
            if cat_name not in custom_category_names:
                vat_settings = BUILT_IN_CATEGORY_VAT_DEFAULTS.get(
                    cat_name,
                    {"applicable": False, "rate": 0.0}
                )
                categories.append({
                    "name": cat_name,
                    "is_built_in": True,
                    "vat_applicable": vat_settings["applicable"],
                    "vat_rate": vat_settings["rate"]
                })
        
        return sorted(categories, key=lambda x: x["name"])
    
    def create_category(self, session_id: str, category_name: str, is_income: bool = False) -> Tuple[bool, str]:
        """Create a new custom category (persisted in database)
        
        Args:
            session_id: Session ID
            category_name: Name of the category
            is_income: True for Income/Sales (VAT Output), False for Expense (VAT Input)
        """
        if not category_name or not category_name.strip():
            return False, "Category name cannot be empty"
        
        category_name = category_name.strip()
        
        if len(category_name) < 2:
            return False, "Category name must be at least 2 characters"
        
        if len(category_name) > 50:
            return False, "Category name must be 50 characters or less"
        
        db = self._get_db()
        try:
            # Check if already exists (case-insensitive)
            existing = self.get_all_categories(session_id)
            if category_name.lower() in [c.lower() for c in existing]:
                return False, f"Category '{category_name}' already exists"
            
            # Create in database with is_income flag
            new_category = CustomCategory(
                name=category_name,
                is_income=1 if is_income else 0
            )
            db.add(new_category)
            db.commit()
            
            cat_type = "Income/Sales (VAT Output)" if is_income else "Expense (VAT Input)"
            return True, f"Category '{category_name}' created as {cat_type}"
        except Exception as e:
            db.rollback()
            return False, f"Failed to create category: {str(e)}"
        finally:
            db.close()
    
    def delete_category(self, session_id: str, category_name: str) -> Tuple[bool, str]:
        """Delete a custom category (cannot delete built-in)"""
        if category_name in BUILT_IN_CATEGORIES:
            return False, "Cannot delete built-in categories"
        
        db = self._get_db()
        try:
            # Find the category in database
            category = db.query(CustomCategory).filter(CustomCategory.name == category_name).first()
            
            if not category:
                return False, "Category not found"
            
            # Delete from database
            db.delete(category)
            db.commit()
            
            # Also remove any rules that used this category (from in-memory rules)
            if session_id in self.session_rules:
                self.session_rules[session_id] = [
                    r for r in self.session_rules[session_id]
                    if r.category != category_name
                ]
            
            return True, f"Category '{category_name}' deleted"
        except Exception as e:
            db.rollback()
            return False, f"Failed to delete category: {str(e)}"
        finally:
            db.close()
    
    def create_rule(
        self,
        session_id: str,
        rule_id: str,
        name: str,
        category: str,
        keywords: List[str],
        priority: int,
        auto_apply: bool = True,
        match_compound_words: bool = False
    ) -> Tuple[bool, str]:
        """Create a new categorization rule
        
        Args:
            match_compound_words: If True, keyword can match in compound words like "RenteOpDTBal".
                                If False (default), keyword must be separate word like "RENT PAYMENT".
        """
        # Validate inputs
        if not name or not name.strip():
            return False, "Rule name cannot be empty"
        
        if not keywords or len(keywords) == 0:
            return False, "Rule must have at least one keyword"
        
        # Validate category exists
        valid_cats = self.get_all_categories(session_id)
        if category not in valid_cats:
            return False, f"Category '{category}' does not exist"
        
        if session_id not in self.session_rules:
            self.session_rules[session_id] = []
        
        # Check rule name doesn't already exist
        if any(r.name == name for r in self.session_rules[session_id]):
            return False, f"Rule '{name}' already exists"
        
        rule = CategoryRule(
            rule_id=rule_id,
            name=name,
            category=category,
            keywords=[kw.strip().lower() for kw in keywords if kw.strip()],
            priority=priority,
            auto_apply=auto_apply,
            enabled=True,
            match_compound_words=match_compound_words
        )
        
        self.session_rules[session_id].append(rule)
        # Re-sort by priority
        self.session_rules[session_id].sort(key=lambda r: r.priority)
        
        return True, f"Rule '{name}' created successfully"
    
    def update_rule(
        self,
        session_id: str,
        rule_id: str,
        **kwargs
    ) -> Tuple[bool, str]:
        """Update an existing rule"""
        if session_id not in self.session_rules:
            return False, "No rules found for this session"
        
        rule_idx = None
        for i, r in enumerate(self.session_rules[session_id]):
            if r.rule_id == rule_id:
                rule_idx = i
                break
        
        if rule_idx is None:
            return False, "Rule not found"
        
        rule = self.session_rules[session_id][rule_idx]
        
        # Update allowed fields
        if "name" in kwargs:
            rule.name = kwargs["name"]
        if "category" in kwargs:
            valid_cats = self.get_all_categories(session_id)
            if kwargs["category"] not in valid_cats:
                return False, f"Category '{kwargs['category']}' does not exist"
            rule.category = kwargs["category"]
        if "keywords" in kwargs:
            rule.keywords = [kw.strip().lower() for kw in kwargs["keywords"] if kw.strip()]
        if "priority" in kwargs:
            rule.priority = kwargs["priority"]
        if "auto_apply" in kwargs:
            rule.auto_apply = kwargs["auto_apply"]
        if "enabled" in kwargs:
            rule.enabled = kwargs["enabled"]
        
        # Re-sort by priority
        self.session_rules[session_id].sort(key=lambda r: r.priority)
        return True, f"Rule '{rule.name}' updated successfully"
    
    def delete_rule(self, session_id: str, rule_id: str) -> Tuple[bool, str]:
        """Delete a rule"""
        if session_id not in self.session_rules:
            return False, "No rules found for this session"
        
        original_len = len(self.session_rules[session_id])
        self.session_rules[session_id] = [
            r for r in self.session_rules[session_id]
            if r.rule_id != rule_id
        ]
        
        if len(self.session_rules[session_id]) == original_len:
            return False, "Rule not found"
        
        return True, "Rule deleted successfully"
    
    def get_rules(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all rules for a session, sorted by priority"""
        if session_id not in self.session_rules:
            return []
        
        return [r.to_dict() for r in self.session_rules[session_id]]
    
    def preview_rule_matches(
        self,
        session_id: str,
        rule_id: str,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Preview which transactions would match a specific rule"""
        if session_id not in self.session_rules:
            return {"matched": [], "count": 0, "percentage": 0}
        
        rule = None
        for r in self.session_rules[session_id]:
            if r.rule_id == rule_id:
                rule = r
                break
        
        if not rule:
            return {"matched": [], "count": 0, "percentage": 0}
        
        matched_txns = []
        for txn in transactions:
            # Don't lowercase before matching - multilingual.match_keyword_in_text handles case-insensitivity
            desc = txn.get("description", "")
            for keyword in rule.keywords:
                # Keywords are already lowercase from storage, but match_keyword_in_text handles case-insensitivity
                # Pass the match_compound_words flag to allow matching in compound words if enabled
                if multilingual.match_keyword_in_text(keyword, desc, strict_boundaries=not rule.match_compound_words):
                    matched_txns.append({
                        "id": txn.get("id"),
                        "date": str(txn.get("date")),
                        "description": txn.get("description"),
                        "amount": txn.get("amount"),
                        "keyword_matched": keyword
                    })
                    break  # Only count once per transaction
        
        percentage = 0
        if len(transactions) > 0:
            percentage = round((len(matched_txns) / len(transactions)) * 100, 1)
        
        return {
            "matched": matched_txns,
            "count": len(matched_txns),
            "percentage": percentage,
            "rule_name": rule.name,
            "category": rule.category
        }
    
    def apply_rules_to_transactions(
        self,
        session_id: str,
        transactions: List[Dict[str, Any]],
        rule_ids: Optional[List[str]] = None,
        auto_apply_only: bool = False
    ) -> Dict[str, Any]:
        """Apply rules to transactions and categorize them"""
        if session_id not in self.session_rules:
            return {"updated": 0, "transactions": transactions}
        
        rules = self.session_rules[session_id]
        
        # Filter rules if specified
        if rule_ids:
            rules = [r for r in rules if r.rule_id in rule_ids]
        
        # Filter by auto_apply if requested
        if auto_apply_only:
            rules = [r for r in rules if r.auto_apply and r.enabled]
        else:
            rules = [r for r in rules if r.enabled]
        
        # Sort by priority (lower number = higher priority)
        rules.sort(key=lambda r: r.priority)
        
        updated_count = 0
        
        for txn in transactions:
            desc = txn.get("description", "")
            
            # Try to match against rules in priority order
            for rule in rules:
                matched = False
                for keyword in rule.keywords:
                    # Use the rule's match_compound_words setting
                    if multilingual.match_keyword_in_text(keyword, desc, strict_boundaries=not rule.match_compound_words):
                        matched = True
                        break
                
                if matched:
                    txn["category"] = rule.category
                    updated_count += 1
                    break  # First match wins
        
        return {
            "updated": updated_count,
            "transactions": transactions,
            "rules_applied": len(rules)
        }
    
    def get_rule_statistics(
        self,
        session_id: str,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get statistics for all rules (how many transactions they would match)"""
        if session_id not in self.session_rules:
            return []
        
        stats = []
        for rule in self.session_rules[session_id]:
            preview = self.preview_rule_matches(session_id, rule.rule_id, transactions)
            stats.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "category": rule.category,
                "priority": rule.priority,
                "auto_apply": rule.auto_apply,
                "enabled": rule.enabled,
                "matched_count": preview["count"],
                "matched_percentage": preview["percentage"],
                "keywords": rule.keywords
            })
        
        return stats
