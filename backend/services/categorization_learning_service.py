"""
Auto-Categorization Learning Service
Learns user categorization patterns and applies them to future transactions
"""

import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime


class CategorizationLearningService:
    """Service for learning and applying user categorization patterns"""
    
    @staticmethod
    def extract_merchant_from_description(description: str) -> Optional[str]:
        """
        Extract a clean merchant name from transaction description
        Handles common bank formats like:
        - "WOOLWORTHS 123 CAPE TOWN"
        - "POS PURCHASE CHECKERS #123"
        - "NETFLIX.COM"
        """
        if not description:
            return None
        
        # Remove common prefixes
        desc = description.strip()
        prefixes_to_remove = [
            r'^POS PURCHASE\s+',
            r'^DEBIT ORDER\s+',
            r'^PAYMENT\s+',
            r'^TRANSFER\s+',
            r'^ATM WITHDRAWAL\s+',
            r'^CASH DEPOSIT\s+',
        ]
        
        for prefix in prefixes_to_remove:
            desc = re.sub(prefix, '', desc, flags=re.IGNORECASE)
        
        # Extract first meaningful word/phrase (before numbers or special chars)
        # Match letters, dots (for domains like NETFLIX.COM), and spaces
        # Updated regex to capture domain-like patterns better
        match = re.match(r'^([A-Z][A-Z\s\.]+?)(?:\s+\d|\s+#|\s+-|$)', desc)
        if match:
            merchant = match.group(1).strip()
            # Clean up extra spaces and trailing dots
            merchant = re.sub(r'\s+', ' ', merchant).strip('.')
            
            # For domain-like patterns (e.g., NETFLIX.COM), keep just the main part
            if '.' in merchant:
                # Extract the main domain part
                parts = merchant.split('.')
                merchant = parts[0]  # e.g., "NETFLIX.COM" → "NETFLIX"
            
            return merchant if len(merchant) > 2 else None
        
        return None
    
    @staticmethod
    def normalize_description(description: str) -> str:
        """Normalize description for pattern matching"""
        # Remove extra whitespace, convert to uppercase
        normalized = re.sub(r'\s+', ' ', description.strip().upper())
        # Remove special characters except spaces and dots
        normalized = re.sub(r'[^A-Z0-9\s\.]', '', normalized)
        return normalized
    
    @staticmethod
    def learn_from_categorization(
        user_id: str,
        session_id: str,
        description: str,
        category: str,
        merchant: Optional[str] = None,
        keyword: Optional[str] = None,
        db: Session = None,
        client_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Save a keyword-based categorization rule so it applies to future uploads.

        A rule is only created when the user explicitly provides a keyword
        (at least 3 characters). This prevents spurious auto-generated rules
        based on noisy, never-repeating transaction descriptions.

        The saved rule is a 'contains' pattern: any future transaction whose
        description contains the keyword will be confirmed as the given category.

        Returns list of created/updated rules (empty if no keyword supplied).
        """
        if not keyword or len(keyword.strip()) < 3:
            return []

        keyword_clean = keyword.strip().upper()
        rule = CategorizationLearningService._create_or_update_rule(
            user_id=user_id,
            session_id=session_id,
            category=category,
            pattern_type='contains',
            pattern_value=keyword_clean,
            db=db,
            client_id=client_id
        )
        return [rule] if rule else []
    
    @staticmethod
    def _create_or_update_rule(
        user_id: str,
        session_id: str,
        category: str,
        pattern_type: str,
        pattern_value: str,
        db: Session,
        client_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Create a new rule or update existing one
        If rule already exists for same pattern but different category, update it
        """
        from models import UserCategorizationRule
        
        # Check if rule already exists for this user + client
        query = db.query(UserCategorizationRule).filter(
            UserCategorizationRule.user_id == user_id,
            UserCategorizationRule.pattern_type == pattern_type,
            UserCategorizationRule.pattern_value == pattern_value
        )
        if client_id is not None:
            query = query.filter(UserCategorizationRule.client_id == client_id)
        else:
            query = query.filter(UserCategorizationRule.client_id.is_(None))
        existing = query.first()
        
        if existing:
            # Update category if different (user changed their mind)
            if existing.category != category:
                existing.category = category
                existing.confidence_score = 1.0  # Reset confidence
                db.commit()
                return {
                    'id': existing.id,
                    'pattern_type': existing.pattern_type,
                    'pattern_value': existing.pattern_value,
                    'category': existing.category,
                    'action': 'updated'
                }
            # Rule already exists with same category, no action needed
            return None
        
        # Create new rule
        new_rule = UserCategorizationRule(
            user_id=user_id,
            client_id=client_id,
            session_id=session_id,
            category=category,
            pattern_type=pattern_type,
            pattern_value=pattern_value,
            confidence_score=1.0,
            use_count=0,
            enabled=1
        )
        db.add(new_rule)
        db.commit()
        
        return {
            'id': new_rule.id,
            'pattern_type': new_rule.pattern_type,
            'pattern_value': new_rule.pattern_value,
            'category': new_rule.category,
            'action': 'created'
        }
    
    @staticmethod
    def apply_learned_rules(
        user_id: str,
        transactions: List,
        db: Session,
        client_id: Optional[int] = None,
        override_existing: bool = False
    ) -> Dict[int, str]:
        """
        Apply learned rules to a list of transactions
        Returns dict of transaction_id -> suggested_category
        
        Prioritizes rules by:
        1. Pattern type (exact > merchant > starts_with > contains)
        2. Confidence score
        3. Use count (more frequently used rules)
        
        Args:
            override_existing: If True, learned rules override any auto-assigned category
                               (use during upload so learned rules beat the built-in categorizer).
                               If False, only apply to uncategorized / 'Other' transactions
                               (use for manual re-apply to avoid overwriting user work).
        """
        from models import UserCategorizationRule
        
        # Get all enabled rules for this user + client, ordered by priority.
        # STRICT client scoping: only load rules for the exact client.
        # When client_id is None, only load rules with NULL client_id (global rules).
        # This prevents rules learned for Client A from applying to Client B.
        query = db.query(UserCategorizationRule).filter(
            UserCategorizationRule.user_id == user_id,
            UserCategorizationRule.enabled == 1
        )
        if client_id is not None:
            query = query.filter(UserCategorizationRule.client_id == client_id)
        else:
            query = query.filter(UserCategorizationRule.client_id.is_(None))
        rules = query.all()
        
        # Group rules by pattern type for efficient matching
        exact_rules = {}
        merchant_rules = {}
        starts_with_rules = []
        contains_rules = []
        
        for rule in rules:
            if rule.pattern_type == 'exact':
                exact_rules[rule.pattern_value] = rule
            elif rule.pattern_type == 'merchant':
                merchant_rules[rule.pattern_value] = rule
            elif rule.pattern_type == 'starts_with':
                starts_with_rules.append(rule)
            elif rule.pattern_type == 'contains':
                contains_rules.append(rule)
        
        # Apply rules to transactions
        suggestions = {}
        
        for txn in transactions:
            # Never override user-confirmed categories unless override_existing is set.
            # Even with override_existing (during upload), respect confirmed Income
            # for positive-amount transactions — learned rules should only override
            # the built-in expense categorizer, not flip income to an expense category.
            if not override_existing:
                if hasattr(txn, 'category') and txn.category and txn.category not in ('Other', 'Uncategorized'):
                    continue
            else:
                # During upload: only override "Uncategorized" / "Other" / built-in suggestions.
                # Never override Income for positive amounts — that's confirmed by the system.
                txn_amount = getattr(txn, 'amount', 0)
                txn_category = getattr(txn, 'category', '')
                if txn_amount is not None and float(txn_amount) > 0 and txn_category == 'Income':
                    continue
                # Also skip if user-created DB rule already confirmed this transaction
                if txn_category and txn_category not in ('Other', 'Uncategorized') and not getattr(txn, 'suggested_category', None):
                    # A DB rule already confirmed this — don't let learned rules fight it
                    pass  # Allow learned rules to override DB-rule confirmations since learned rules are more recent user intent
            
            description = txn.description if hasattr(txn, 'description') else str(txn)
            normalized_desc = CategorizationLearningService.normalize_description(description)
            
            matched_rule = None
            
            # 1. Try exact match first (highest priority)
            if normalized_desc in exact_rules:
                matched_rule = exact_rules[normalized_desc]
            
            # 2. Try merchant match (check both merchant field and extracted merchant)
            if not matched_rule:
                # First try the actual merchant field if it exists
                txn_merchant = getattr(txn, 'merchant', None)
                if txn_merchant and txn_merchant.strip():
                    merchant_upper = txn_merchant.strip().upper()
                    if merchant_upper in merchant_rules:
                        matched_rule = merchant_rules[merchant_upper]
                
                # Fall back to extracting merchant from description
                if not matched_rule:
                    extracted_merchant = CategorizationLearningService.extract_merchant_from_description(description)
                    if extracted_merchant and extracted_merchant.upper() in merchant_rules:
                        matched_rule = merchant_rules[extracted_merchant.upper()]
            
            # 3. Try starts_with patterns
            if not matched_rule:
                for rule in starts_with_rules:
                    if normalized_desc.startswith(rule.pattern_value):
                        matched_rule = rule
                        break
            
            # 4. Try contains patterns (lowest priority)
            if not matched_rule:
                for rule in contains_rules:
                    if rule.pattern_value in normalized_desc:
                        matched_rule = rule
                        break
            
            # Apply matched rule
            if matched_rule:
                txn_id = txn.id if hasattr(txn, 'id') else None
                if txn_id:
                    suggestions[txn_id] = matched_rule.category
                    
                    # Update rule usage statistics
                    matched_rule.use_count += 1
                    matched_rule.last_used = datetime.utcnow()
        
        db.commit()
        return suggestions
    
    @staticmethod
    def get_learned_rules(user_id: str, db: Session, client_id: Optional[int] = None) -> List[Dict]:
        """Get all learned rules for a user, optionally scoped to a client"""
        from models import UserCategorizationRule
        
        # STRICT client scoping: only return rules for the exact client.
        # When client_id is None, only return rules with NULL client_id (global).
        query = db.query(UserCategorizationRule).filter(
            UserCategorizationRule.user_id == user_id
        )
        if client_id is not None:
            query = query.filter(UserCategorizationRule.client_id == client_id)
        else:
            query = query.filter(UserCategorizationRule.client_id.is_(None))
        rules = query.order_by(
            UserCategorizationRule.use_count.desc(),
            UserCategorizationRule.created_at.desc()
        ).all()
        
        return [
            {
                'id': rule.id,
                'category': rule.category,
                'pattern_type': rule.pattern_type,
                'pattern_value': rule.pattern_value,
                'confidence_score': rule.confidence_score,
                'use_count': rule.use_count,
                'enabled': rule.enabled == 1,
                'created_at': rule.created_at.isoformat() if rule.created_at else None,
                'last_used': rule.last_used.isoformat() if rule.last_used else None
            }
            for rule in rules
        ]
    
    @staticmethod
    def update_rule(
        rule_id: int,
        user_id: str,
        updates: Dict,
        db: Session
    ) -> Tuple[bool, str]:
        """Update a learned rule"""
        from models import UserCategorizationRule
        
        rule = db.query(UserCategorizationRule).filter(
            UserCategorizationRule.id == rule_id,
            UserCategorizationRule.user_id == user_id
        ).first()
        
        if not rule:
            return False, "Rule not found"
        
        # Update allowed fields
        if 'category' in updates:
            rule.category = updates['category']
        if 'enabled' in updates:
            rule.enabled = 1 if updates['enabled'] else 0
        if 'pattern_value' in updates:
            rule.pattern_value = updates['pattern_value']
        
        db.commit()
        return True, "Rule updated successfully"
    
    @staticmethod
    def delete_rule(rule_id: int, user_id: str, db: Session) -> Tuple[bool, str]:
        """Delete a learned rule"""
        from models import UserCategorizationRule
        
        rule = db.query(UserCategorizationRule).filter(
            UserCategorizationRule.id == rule_id,
            UserCategorizationRule.user_id == user_id
        ).first()
        
        if not rule:
            return False, "Rule not found"
        
        db.delete(rule)
        db.commit()
        return True, "Rule deleted successfully"
