from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional
import re

STOP_WORDS = {"pty", "ltd", "payment", "eft", "ppd", "pvt", "ptyltd", "limited"}


def _clean_supplier(s: Optional[str]) -> str:
    if not s:
        return ""
    
    import re
    original = s.strip()
    s_lower = original.lower()
    
    # Strategy: Try to extract company name by finding company suffixes
    company_suffix_pattern = r'(\b(?:pty|ltd|limited|llc|inc|corp|company|co|llp|gmbh|sa|ag|ab|bv|nv|cv|as)\b)'
    
    matches = list(re.finditer(company_suffix_pattern, s_lower))
    if matches:
        # Find the first significant word (non-punctuation) before the company suffix(es)
        first_match = matches[0]
        before_suffix = s_lower[:first_match.start()]
        # Remove punctuation first, then split
        before_clean = re.sub(r"[^a-z0-9\s]", " ", before_suffix)
        words = [w for w in before_clean.split() if w.strip()]
        
        if words:
            # The company name is the last alphanumeric word before the suffix
            company_word = words[-1]
            # Find it in the original string
            company_start = original.lower().find(company_word)
            if company_start >= 0:
                # Get up to and including all company suffixes
                last_match = matches[-1]
                company_name = original[company_start:last_match.end()]
            else:
                company_name = original[:matches[-1].end()]
        else:
            # No significant words before suffix
            company_name = original[:matches[-1].end()]
    else:
        # No company suffix found
        # For bank descriptions, extract first significant word
        words = original.split()
        banking_words = {'fnb', 'app', 'payment', 'to', 'transfer', 'from', 'eft', 'ppd', 'pmt'}
        for word in words:
            if word.lower() not in banking_words and len(word) > 2:
                company_name = word
                break
        else:
            company_name = words[0] if words else original
    
    # Clean the extracted company name
    company_clean = company_name.lower()
    # Remove punctuation
    company_clean = re.sub(r"[^a-z0-9\s]", " ", company_clean)
    # Split and filter
    parts = [p.strip() for p in company_clean.split() if p.strip()]
    parts = [p for p in parts if p not in STOP_WORDS and len(p) > 0]
    
    return " ".join(parts)


def _fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def score_match(invoice: Dict[str, Any], txn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply deterministic matching rules and return score and explanation.

    Rules (ordered):
      - Exact Amount Match: abs diff <= 1.00 => +50
      - Date Proximity: invoice_date within ±7 days => +25
      - Supplier Name Match: fuzzy match (ratio >= 0.7) => +25

    Returns dict: { score:int, classification:str, matched: {amount:bool,date:bool,supplier:bool}, explanation:str }
    """
    score = 0
    matched = {"amount": False, "date": False, "supplier": False}
    reasons: List[str] = []

    # Amount
    try:
        inv_amt = float(invoice.get("total_amount") or 0.0)
        txn_amt = float(txn.get("amount") or 0.0)
        # Bank transactions are typically negative (debits), so compare absolute values
        txn_amt_abs = abs(txn_amt)
        amt_diff = abs(inv_amt - txn_amt_abs)
        if amt_diff <= 1.0:
            score += 50
            matched["amount"] = True
            reasons.append(f"Amount within £1 (diff £{amt_diff:.2f})")
        else:
            reasons.append(f"Amount diff £{amt_diff:.2f}")
    except Exception:
        reasons.append("Amount comparison failed")

    # Date proximity
    try:
        inv_date = invoice.get("invoice_date")
        txn_date = txn.get("date")
        if isinstance(inv_date, str):
            inv_date = datetime.fromisoformat(inv_date).date()
        if isinstance(txn_date, str):
            txn_date = datetime.fromisoformat(txn_date).date()
        if inv_date and txn_date:
            delta = abs((inv_date - txn_date).days)
            if delta <= 7:
                score += 25
                matched["date"] = True
                reasons.append(f"Date within {delta} day(s)")
            else:
                reasons.append(f"Date delta {delta} day(s)")
    except Exception:
        reasons.append("Date comparison failed")

    # Supplier fuzzy match
    try:
        inv_sup = _clean_supplier(invoice.get("supplier_name") or "")
        txn_desc = _clean_supplier(txn.get("description") or "")
        ratio = _fuzzy_ratio(inv_sup, txn_desc)
        if ratio >= 0.70:
            score += 25
            matched["supplier"] = True
            reasons.append(f"Supplier fuzzy match ratio {ratio:.2f}")
        else:
            reasons.append(f"Supplier ratio {ratio:.2f}")
    except Exception:
        reasons.append("Supplier comparison failed")

    # Classification
    classification = "Low"
    if score >= 80:
        classification = "High"
    elif score >= 50:
        classification = "Medium"

    explanation = ", ".join(reasons)

    return {
        "score": int(score),
        "classification": classification,
        "matched": matched,
        "explanation": explanation,
        "amount_diff": round(abs((invoice.get("total_amount") or 0.0) - (txn.get("amount") or 0.0)), 2),
    }


def find_best_matches(invoices: List[Dict[str, Any]], txns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    For each invoice, evaluate all transactions and return best match info.
    Returns list of { invoice_id, invoice, best_match_txn_id, txn, score, classification, explanation }
    """
    results = []
    for inv in invoices:
        best = None
        best_meta = None
        for t in txns:
            meta = score_match(inv, t)
            key = (meta['score'], -meta.get('amount_diff', 99999), )
            if best is None:
                best = (t, meta)
                best_meta = meta
            else:
                # choose larger score; tiebreaker: smaller amount diff, then smaller date delta (embedded in explanation)
                if meta['score'] > best_meta['score']:
                    best = (t, meta)
                    best_meta = meta
                elif meta['score'] == best_meta['score']:
                    if meta.get('amount_diff', 99999) < best_meta.get('amount_diff', 99999):
                        best = (t, meta)
                        best_meta = meta

        if best:
            results.append({
                "invoice_id": inv.get("id"),
                "invoice": inv,
                "transaction_id": best[0].get("id"),
                "transaction": best[0],
                "score": best[1]["score"],
                "classification": best[1]["classification"],
                "explanation": best[1]["explanation"],
                "matched": best[1]["matched"]
            })
        else:
            results.append({
                "invoice_id": inv.get("id"),
                "invoice": inv,
                "transaction_id": None,
                "transaction": None,
                "score": 0,
                "classification": "Low",
                "explanation": "No candidate transactions"
            })

    return results
