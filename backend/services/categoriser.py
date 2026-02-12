"""
Transaction Categorizer Service
Rules-based categorization (NOT AI)

EDIT THIS FILE TO ADD NEW CATEGORIES OR MODIFY RULES
Business logic for categorizing transactions is kept HERE for easy maintenance
"""

import json
import os
import re
from typing import Tuple, List, Dict


# =============================================================================
# MERCHANT MAPPINGS - Comprehensive database for automatic merchant normalization
# =============================================================================

MERCHANT_MAPPINGS = [
    # =========================================================================
    # FUEL STATIONS - South African
    # =========================================================================
    {
        "merchant": "Shell",
        "patterns": ["shell", "shell fuel", "shell garage", "shell service", "shell express", "shell select"],
        "category": "Fuel"
    },
    {
        "merchant": "Engen",
        "patterns": ["engen", "engen garage", "engen quick", "engen service", "engen 1 stop"],
        "category": "Fuel"
    },
    {
        "merchant": "BP",
        "patterns": ["bp ", "bp fuel", "bp garage", "bp service station", "british petroleum"],
        "category": "Fuel"
    },
    {
        "merchant": "Caltex",
        "patterns": ["caltex", "caltex star", "caltex garage", "caltex service"],
        "category": "Fuel"
    },
    {
        "merchant": "Sasol",
        "patterns": ["sasol", "sasol garage", "sasol convenience"],
        "category": "Fuel"
    },
    {
        "merchant": "Total",
        "patterns": ["total ", "total energies", "total fuel", "total garage"],
        "category": "Fuel"
    },
    
    # =========================================================================
    # SUPERMARKETS & GROCERIES - South African
    # =========================================================================
    {
        "merchant": "Shoprite",
        "patterns": ["shoprite", "shoprite checkers", "shoprite supermarket"],
        "category": "Groceries"
    },
    {
        "merchant": "Checkers",
        "patterns": ["checkers", "checkers hyper", "checkers sixty60"],
        "category": "Groceries"
    },
    {
        "merchant": "Woolworths",
        "patterns": ["woolworths", "woolies", "woolworth", "woolworths food"],
        "category": "Groceries"
    },
    {
        "merchant": "Pick n Pay",
        "patterns": ["pick n pay", "pick'n pay", "picknpay", "pnp"],
        "category": "Groceries"
    },
    {
        "merchant": "Spar",
        "patterns": ["spar ", "superspar", "kwikspar", "spar supermarket"],
        "category": "Groceries"
    },
    {
        "merchant": "Makro",
        "patterns": ["makro", "makro wholesale"],
        "category": "Groceries"
    },
    {
        "merchant": "Game",
        "patterns": ["game stores", "game discount", "game liquor"],
        "category": "Groceries"
    },
    {
        "merchant": "Boxer",
        "patterns": ["boxer stores", "boxer superstores"],
        "category": "Groceries"
    },
    {
        "merchant": "Food Lover's Market",
        "patterns": ["food lovers", "food lover's", "flm "],
        "category": "Groceries"
    },
    {
        "merchant": "Cambridge Food",
        "patterns": ["cambridge food", "cambridge foods"],
        "category": "Groceries"
    },
    {
        "merchant": "Fruit & Veg City",
        "patterns": ["fruit and veg", "fruit & veg", "fnv city"],
        "category": "Groceries"
    },
    
    # =========================================================================
    # FAST FOOD & RESTAURANTS - South African
    # =========================================================================
    {
        "merchant": "McDonald's",
        "patterns": ["mcdonalds", "mcdonald's", "mc donalds", "mcd "],
        "category": "Meals & Dining"
    },
    {
        "merchant": "KFC",
        "patterns": ["kfc ", "kentucky fried"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Nando's",
        "patterns": ["nandos", "nando's", "nandos peri"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Steers",
        "patterns": ["steers", "steers burger"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Wimpy",
        "patterns": ["wimpy"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Spur",
        "patterns": ["spur steak", "spur grill"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Debonairs Pizza",
        "patterns": ["debonairs", "debonair pizza"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Domino's Pizza",
        "patterns": ["dominos", "domino's pizza", "domino pizza"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Roman's Pizza",
        "patterns": ["romans pizza", "roman's pizza"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Burger King",
        "patterns": ["burger king", "bk "],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Pizza Hut",
        "patterns": ["pizza hut", "pizzahut"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Ocean Basket",
        "patterns": ["ocean basket"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Mugg & Bean",
        "patterns": ["mugg and bean", "mugg & bean", "mugg bean"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Vida e Caffè",
        "patterns": ["vida e caffe", "vida caffe", "vida"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Starbucks",
        "patterns": ["starbucks", "starbucks coffee"],
        "category": "Meals & Dining"
    },
    
    # =========================================================================
    # FOOD DELIVERY SERVICES
    # =========================================================================
    {
        "merchant": "Uber Eats",
        "patterns": ["uber eats", "ubereats"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Mr D Food",
        "patterns": ["mr d food", "mr. d food", "mrd food"],
        "category": "Meals & Dining"
    },
    {
        "merchant": "Checkers Sixty60",
        "patterns": ["sixty60", "60sixty", "checkers sixty"],
        "category": "Groceries"
    },
    
    # =========================================================================
    # RETAIL STORES - South African
    # =========================================================================
    {
        "merchant": "TakeAlot",
        "patterns": ["takealot", "take alot", "takealot.com"],
        "category": "Other"
    },
    {
        "merchant": "Mr Price",
        "patterns": ["mr price", "mrp ", "mr price home", "mr price sport"],
        "category": "Other"
    },
    {
        "merchant": "Edgars",
        "patterns": ["edgars", "edgars stores"],
        "category": "Other"
    },
    {
        "merchant": "Truworths",
        "patterns": ["truworths"],
        "category": "Other"
    },
    {
        "merchant": "Woolworths",
        "patterns": ["woolworths fashion", "woolworths clothing"],
        "category": "Other"
    },
    {
        "merchant": "Ackermans",
        "patterns": ["ackermans", "ackerman"],
        "category": "Other"
    },
    {
        "merchant": "PEP",
        "patterns": ["pep stores", "pep cell"],
        "category": "Other"
    },
    {
        "merchant": "CNA",
        "patterns": ["cna stores", "cna "],
        "category": "Office & Supplies"
    },
    {
        "merchant": "Dis-Chem",
        "patterns": ["dischem", "dis-chem", "dis chem"],
        "category": "Healthcare"
    },
    {
        "merchant": "Clicks",
        "patterns": ["clicks", "clicks pharmacy"],
        "category": "Healthcare"
    },
    
    # =========================================================================
    # UTILITIES & SERVICES - South African
    # =========================================================================
    {
        "merchant": "Eskom",
        "patterns": ["eskom", "electricity"],
        "category": "Utilities"
    },
    {
        "merchant": "Vodacom",
        "patterns": ["vodacom", "vodacom airtime", "vodacom data"],
        "category": "Utilities"
    },
    {
        "merchant": "MTN",
        "patterns": ["mtn ", "mtn airtime", "mtn data"],
        "category": "Utilities"
    },
    {
        "merchant": "Cell C",
        "patterns": ["cell c", "cellc"],
        "category": "Utilities"
    },
    {
        "merchant": "Telkom",
        "patterns": ["telkom", "telkom mobile"],
        "category": "Utilities"
    },
    {
        "merchant": "Rain",
        "patterns": ["rain mobile", "rain data"],
        "category": "Utilities"
    },
    {
        "merchant": "DStv",
        "patterns": ["dstv", "multichoice", "mnet"],
        "category": "Entertainment"
    },
    {
        "merchant": "Showmax",
        "patterns": ["showmax"],
        "category": "Entertainment"
    },
    
    # =========================================================================
    # BANKS - South African
    # =========================================================================
    {
        "merchant": "FNB",
        "patterns": ["fnb ", "first national bank"],
        "category": "Fees & Charges"
    },
    {
        "merchant": "Standard Bank",
        "patterns": ["standard bank", "standardbank"],
        "category": "Fees & Charges"
    },
    {
        "merchant": "ABSA",
        "patterns": ["absa", "absa bank"],
        "category": "Fees & Charges"
    },
    {
        "merchant": "Nedbank",
        "patterns": ["nedbank"],
        "category": "Fees & Charges"
    },
    {
        "merchant": "Capitec",
        "patterns": ["capitec", "capitec bank"],
        "category": "Fees & Charges"
    },
    {
        "merchant": "Discovery Bank",
        "patterns": ["discovery bank"],
        "category": "Fees & Charges"
    },
    {
        "merchant": "TymeBank",
        "patterns": ["tymebank", "tyme bank"],
        "category": "Fees & Charges"
    },
    {
        "merchant": "African Bank",
        "patterns": ["african bank"],
        "category": "Fees & Charges"
    },
    
    # =========================================================================
    # TRANSPORTATION - South African & International
    # =========================================================================
    {
        "merchant": "Uber",
        "patterns": ["uber ", "uber trip", "uber ride"],
        "category": "Transportation"
    },
    {
        "merchant": "Bolt",
        "patterns": ["bolt ", "bolt ride", "taxify"],
        "category": "Transportation"
    },
    {
        "merchant": "inDrive",
        "patterns": ["indrive"],
        "category": "Transportation"
    },
    {
        "merchant": "South African Airways",
        "patterns": ["saa ", "south african airways"],
        "category": "Transportation"
    },
    {
        "merchant": "British Airways",
        "patterns": ["british airways", "ba "],
        "category": "Transportation"
    },
    {
        "merchant": "FlySafair",
        "patterns": ["flysafair", "safair"],
        "category": "Transportation"
    },
    {
        "merchant": "Kulula",
        "patterns": ["kulula"],
        "category": "Transportation"
    },
    {
        "merchant": "Mango Airlines",
        "patterns": ["mango airlines"],
        "category": "Transportation"
    },
    
    # =========================================================================
    # INTERNATIONAL ONLINE SERVICES
    # =========================================================================
    {
        "merchant": "Netflix",
        "patterns": ["netflix"],
        "category": "Entertainment"
    },
    {
        "merchant": "Amazon",
        "patterns": ["amazon", "amzn", "amazon.com", "amazon prime"],
        "category": "Subscriptions"
    },
    {
        "merchant": "Amazon Prime",
        "patterns": ["amazon prime", "prime video"],
        "category": "Subscriptions"
    },
    {
        "merchant": "Spotify",
        "patterns": ["spotify"],
        "category": "Entertainment"
    },
    {
        "merchant": "Apple",
        "patterns": ["apple.com", "apple store", "itunes", "app store"],
        "category": "Subscriptions"
    },
    {
        "merchant": "Google",
        "patterns": ["google play", "google storage", "google one", "youtube premium"],
        "category": "Subscriptions"
    },
    {
        "merchant": "Microsoft",
        "patterns": ["microsoft", "msft", "office 365", "microsoft 365"],
        "category": "Subscriptions"
    },
    {
        "merchant": "PayPal",
        "patterns": ["paypal"],
        "category": "Transfers"
    },
    {
        "merchant": "Steam",
        "patterns": ["steam games", "steampowered"],
        "category": "Entertainment"
    },
    {
        "merchant": "PlayStation",
        "patterns": ["playstation", "ps store", "sony entertainment"],
        "category": "Entertainment"
    },
    {
        "merchant": "Xbox",
        "patterns": ["xbox", "xbox live", "xbox game pass"],
        "category": "Entertainment"
    },
    {
        "merchant": "Dropbox",
        "patterns": ["dropbox"],
        "category": "Subscriptions"
    },
    {
        "merchant": "Adobe",
        "patterns": ["adobe", "adobe creative"],
        "category": "Subscriptions"
    },
    {
        "merchant": "Zoom",
        "patterns": ["zoom.us", "zoom video"],
        "category": "Subscriptions"
    },
    
    # =========================================================================
    # INSURANCE - South African
    # =========================================================================
    {
        "merchant": "Discovery",
        "patterns": ["discovery life", "discovery insure", "discovery health"],
        "category": "Insurance"
    },
    {
        "merchant": "Old Mutual",
        "patterns": ["old mutual"],
        "category": "Insurance"
    },
    {
        "merchant": "Sanlam",
        "patterns": ["sanlam"],
        "category": "Insurance"
    },
    {
        "merchant": "Momentum",
        "patterns": ["momentum"],
        "category": "Insurance"
    },
    {
        "merchant": "Hollard",
        "patterns": ["hollard"],
        "category": "Insurance"
    },
    {
        "merchant": "King Price Insurance",
        "patterns": ["king price", "kingprice"],
        "category": "Insurance"
    },
    {
        "merchant": "Budget Insurance",
        "patterns": ["budget insurance"],
        "category": "Insurance"
    },
    {
        "merchant": "MiWay",
        "patterns": ["miway", "mi-way"],
        "category": "Insurance"
    },
    {
        "merchant": "Outsurance",
        "patterns": ["outsurance", "outsure"],
        "category": "Insurance"
    },
    
    # =========================================================================
    # GYM & FITNESS - South African
    # =========================================================================
    {
        "merchant": "Virgin Active",
        "patterns": ["virgin active"],
        "category": "Entertainment"
    },
    {
        "merchant": "Planet Fitness",
        "patterns": ["planet fitness"],
        "category": "Entertainment"
    },
    {
        "merchant": "Fitness First",
        "patterns": ["fitness first"],
        "category": "Entertainment"
    },
    
    # =========================================================================
    # EDUCATION - South African
    # =========================================================================
    {
        "merchant": "Curro",
        "patterns": ["curro schools", "curro holdings"],
        "category": "Other"
    },
    {
        "merchant": "ADvTECH",
        "patterns": ["advtech", "crawford"],
        "category": "Other"
    },
    
    # =========================================================================
    # PETROL ATTENDANT TIPS & PARKING
    # =========================================================================
    {
        "merchant": "Parking",
        "patterns": ["parking", "parkade", "car park"],
        "category": "Transportation"
    },
    {
        "merchant": "Toll",
        "patterns": ["toll ", "e-toll", "sanral"],
        "category": "Transportation"
    },
]


# =============================================================================
# DEFAULT CATEGORIES
# =============================================================================

DEFAULT_CATEGORIES = [
    "Rent",
    "Utilities",
    "Fuel",
    "Groceries",
    "Meals & Dining",
    "Transportation",
    "Healthcare",
    "Insurance",
    "Office & Supplies",
    "Professional Services",
    "Subscriptions",
    "Entertainment",
    "Gifts & Donations",
    "Fees & Charges",
    "Transfers",
    "Income",
    "Other"
]


# =============================================================================
# CATEGORIZATION RULES
# Edit these rules to customize how transactions are categorized
# Each rule is: (category, keywords, exclude_keywords)
# =============================================================================

CATEGORIZATION_RULES = [
    # RENT - landlord, lease, rent, property management
    {
        "category": "Rent",
        "keywords": ["rent", "landlord", "lease", "property mgmt", "property management"],
        "exclude_keywords": []
    },
    
    # UTILITIES - electricity, water, gas, internet, phone
    {
        "category": "Utilities",
        "keywords": ["electricity", "eskom", "water", "gas", "internet", "isp", "dstv", "fibre", "vodacom", "telkom"],
        "exclude_keywords": []
    },
    
    # FUEL - petrol, diesel, fuel, transport
    {
        "category": "Fuel",
        "keywords": ["fuel", "petrol", "diesel", "shell", "caltex", "bp", "engen", "jt", "transport", "uber"],
        "exclude_keywords": []
    },
    
    # GROCERIES - supermarket, food, groceries, restaurant (moderate amounts)
    {
        "category": "Groceries",
        "keywords": ["groceries", "supermarket", "shoprite", "checkers", "takealot", "spar", "food", "coles"],
        "exclude_keywords": []
    },
    
    # MEALS & DINING - restaurant, cafe, pizza, burger, coffee
    {
        "category": "Meals & Dining",
        "keywords": ["restaurant", "cafe", "pizza", "burger", "coffee", "kfc", "mcdonalds", "dominos", "nando's", "steers"],
        "exclude_keywords": []
    },
    
    # TRANSPORTATION - flights, buses, taxis, parking, car rental
    {
        "category": "Transportation",
        "keywords": ["flight", "airline", "bus", "taxi", "parking", "car rental", "hotel", "airbnb"],
        "exclude_keywords": []
    },
    
    # HEALTHCARE - pharmacy, doctor, dentist, hospital, medical
    {
        "category": "Healthcare",
        "keywords": ["pharmacy", "doctor", "dentist", "hospital", "medical", "clinic", "health", "gp"],
        "exclude_keywords": []
    },
    
    # INSURANCE - insurance premium, policy
    {
        "category": "Insurance",
        "keywords": ["insurance", "premium", "policy", "assurance"],
        "exclude_keywords": []
    },
    
    # OFFICE & SUPPLIES - stationery, office, supplies, paper
    {
        "category": "Office & Supplies",
        "keywords": ["stationery", "office", "supplies", "paper", "printer", "ink"],
        "exclude_keywords": []
    },
    
    # PROFESSIONAL SERVICES - legal, accounting, consulting, professional
    {
        "category": "Professional Services",
        "keywords": ["legal", "accounting", "consultant", "professional", "lawyer", "attorney", "audit"],
        "exclude_keywords": []
    },
    
    # SUBSCRIPTIONS - monthly, recurring, annual subscription
    {
        "category": "Subscriptions",
        "keywords": ["subscription", "monthly", "annual subscription", "premium", "membership"],
        "exclude_keywords": []
    },
    
    # ENTERTAINMENT - cinema, movies, games, sports, entertainment
    {
        "category": "Entertainment",
        "keywords": ["cinema", "movie", "games", "sports", "entertainment", "theatre", "museum"],
        "exclude_keywords": []
    },
    
    # GIFTS & DONATIONS - donation, gift, charity
    {
        "category": "Gifts & Donations",
        "keywords": ["donation", "gift", "charity", "contribute"],
        "exclude_keywords": []
    },
    
    # FEES - bank fees, transfer fees, admin fees
    {
        "category": "Fees & Charges",
        "keywords": ["fee", "charge", "admin", "transfer fee", "service charge", "bank charge"],
        "exclude_keywords": []
    },
    
    # TRANSFERS - transfer between accounts
    {
        "category": "Transfers",
        "keywords": ["transfer", "payment received", "payment sent"],
        "exclude_keywords": []
    },
    
    # INCOME - salary, deposit, transfer from, income, revenue
    {
        "category": "Income",
        "keywords": ["salary", "deposit", "income", "revenue", "refund", "credit"],
        "exclude_keywords": []
    },
]


# Attempt to load external rules from services/rules.json to allow easy expansion
def _load_external_rules() -> List[Dict]:
    try:
        base = os.path.dirname(__file__)
        rules_path = os.path.join(base, "rules.json")
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list) and data:
                    # normalize keys
                    normalized = []
                    for r in data:
                        nr = dict(r)
                        nr.setdefault("keywords", [])
                        nr.setdefault("exclude_keywords", [])
                        nr.setdefault("regex", None)
                        nr.setdefault("priority", 0)
                        normalized.append(nr)
                    return normalized
    except Exception:
        pass
    return []


# If an external rules.json exists, prefer it (it can include many more rules)
_external_rules = _load_external_rules()
if _external_rules:
    CATEGORIZATION_RULES = _external_rules



def categorize_transaction(description: str, amount: float) -> Tuple[str, bool]:
    """
    Categorize a transaction based on description and amount
    Uses rule-based matching, NOT AI
    
    Args:
        description: Transaction description (e.g., "SHELL FUEL 001")
        amount: Transaction amount (negative for expenses, positive for income)
        
    Returns:
        Tuple of (category, is_expense)
        - category: One of the predefined categories
        - is_expense: True if negative amount (expense), False if positive (income)
    """
    
    # Determine if expense or income
    is_expense = amount < 0
    
    # Auto-categorize income/deposits
    if not is_expense:
        # Check if description suggests income
        desc_lower = description.lower()
        for rule in CATEGORIZATION_RULES:
            if rule["category"] == "Income":
                if _matches_rule(desc_lower, rule):
                    return rule["category"], is_expense
        # Default income to Income category
        return "Income", is_expense
    
    # Categorize expenses based on rules
    desc_lower = description.lower()
    
    # Check each rule in order (first match wins)
    for rule in CATEGORIZATION_RULES:
        if rule["category"] == "Income":
            continue  # Skip income rules for expenses
        
        if _matches_rule(desc_lower, rule):
            return rule["category"], is_expense
    
    # Default to Other if no match
    return "Other", is_expense


def _matches_rule(description_lower: str, rule: dict) -> bool:
    """
    Check if description matches a categorization rule
    
    Args:
        description_lower: Transaction description (already lowercased)
        rule: Rule dict with keywords and exclude_keywords
        
    Returns:
        True if description matches the rule
    """
    
    # Check regex first (if present)
    regex = rule.get("regex")
    if regex:
        try:
            if re.search(regex, description_lower, flags=re.IGNORECASE):
                # still check excludes
                if rule.get("exclude_keywords"):
                    exclude_match = any(k.lower() in description_lower for k in rule.get("exclude_keywords", []))
                    if exclude_match:
                        return False
                return True
        except re.error:
            pass

    # Check if any keyword matches
    keyword_match = any(
        keyword.lower() in description_lower
        for keyword in rule.get("keywords", [])
    )
    
    if not keyword_match:
        return False
    
    # Check if any exclude keyword matches (if so, rule doesn't apply)
    if rule.get("exclude_keywords"):
        exclude_match = any(
            keyword.lower() in description_lower
            for keyword in rule["exclude_keywords"]
        )
        if exclude_match:
            return False
    
    return True


def get_available_categories() -> list:
    """Return list of available transaction categories"""
    categories = []
    seen = set()
    
    for rule in CATEGORIZATION_RULES:
        cat = rule["category"]
        if cat not in seen:
            categories.append(cat)
            seen.add(cat)
    
    # Ensure Other is always at the end
    if "Other" in categories:
        categories.remove("Other")
    categories.append("Other")
    
    return categories


def normalize_merchant(description: str) -> str:
    """
    Normalize merchant name based on predefined merchant mappings.
    
    Args:
        description: Transaction description
        
    Returns:
        Normalized merchant name if found in mappings, otherwise the extracted merchant name
    """
    if not description:
        return ''
    
    desc_lower = description.lower()
    
    # Check against all merchant mappings
    for mapping in MERCHANT_MAPPINGS:
        for pattern in mapping.get("patterns", []):
            if pattern.lower() in desc_lower:
                return mapping["merchant"]
    
    # If no match found, fall back to heuristic extraction
    return extract_merchant_heuristic(description)


def extract_merchant_heuristic(description: str) -> str:
    """
    Heuristic extraction of a merchant name from transaction description.
    Rules:
      - Split description into tokens and stop when a token contains digits or '*' or is a month abbreviation.
      - Join initial tokens as merchant.
      - Fallback to the full cleaned description truncated to 64 chars.
    """
    import re
    months = set(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])
    if not description:
        return ''
    s = description.strip()
    # remove extra punctuation at ends
    s = re.sub(r'[,:\-]+$', '', s).strip()
    tokens = s.split()
    merchant_tokens = []
    for tok in tokens:
        low = tok.lower().strip(' ,.-')
        if any(ch.isdigit() for ch in tok) or '*' in tok or low in months:
            break
        merchant_tokens.append(tok)

    if merchant_tokens:
        name = ' '.join(merchant_tokens)
    else:
        # fallback: take the first 3 tokens
        name = ' '.join(tokens[:3])

    return name[:64]


def extract_merchant(description: str) -> str:
    """
    Extract and normalize merchant name from transaction description.
    First tries to match against predefined merchant mappings for standardization,
    then falls back to heuristic extraction.
    
    Args:
        description: Transaction description
        
    Returns:
        Normalized merchant name
    """
    return normalize_merchant(description)


def get_merchant_category(merchant_name: str) -> str:
    """
    Get the suggested category for a known merchant.
    
    Args:
        merchant_name: Normalized merchant name
        
    Returns:
        Suggested category for the merchant, or None if not found
    """
    for mapping in MERCHANT_MAPPINGS:
        if mapping["merchant"].lower() == merchant_name.lower():
            return mapping.get("category")
    return None


def get_all_predefined_merchants() -> list:
    """
    Get a list of all predefined merchants in the system.
    Useful for autocomplete or showing available merchants.
    
    Returns:
        List of tuples (merchant_name, category)
    """
    return [(m["merchant"], m.get("category", "Other")) for m in MERCHANT_MAPPINGS]
