"""
Test comprehensive merchant normalization
Shows how various transaction descriptions are normalized to standard merchant names
"""

import sys
sys.path.insert(0, '.')

from services.categoriser import extract_merchant, get_merchant_category, get_all_predefined_merchants

print("🏪 Testing Comprehensive Merchant Normalization\n")
print("=" * 80)

# Test cases with various merchant description formats
test_descriptions = [
    # Fuel stations
    "SHELL FUEL 12345 SANDTON",
    "ENGEN GARAGE CENTURY CITY",
    "BP SERVICE STATION ROODEPOORT",
    "CALTEX STAR SHOP PRETORIA",
    
    # Supermarkets
    "SHOPRITE CHECKERS ROSEBANK",
    "WOOLWORTHS FOOD SANDTON",
    "PICK N PAY FAMILY CENTURION",
    "SPAR SUPERMARKET BELLVILLE",
    
    # Fast food
    "MCDONALDS MENLYN 15 NOV",
    "KFC EASTGATE 11:34",
    "NANDOS PERI PERI SANDTON",
    "STEERS BURGER PRETORIA",
    
    # Utilities
    "VODACOM AIRTIME PURCHASE",
    "DSTV SUBSCRIPTION PAYMENT",
    "ESKOM ELECTRICITY PRE-PAID",
    
    # Online services
    "NETFLIX.COM SUBSCRIPTION",
    "TAKEALOT.COM ORDER #12345",
    "UBER EATS DELIVERY",
    "AMAZON PRIME VIDEO",
    
    # Transportation
    "UBER TRIP 15 JAN 2024",
    "BOLT RIDE SANDTON",
    
    # Insurance
    "DISCOVERY LIFE PREMIUM",
    "OLD MUTUAL POLICY PAYMENT",
    
    # Banks
    "FNB SERVICE FEE",
    "CAPITEC BANK CHARGE",
    
    # Pharmacies
    "CLICKS PHARMACY SANDTON",
    "DISCHEM MENLYN",
    
    # Unknown merchant (will use heuristic)
    "LOCAL BAKERY JHB 001",
    "RANDOM STORE 12345",
]

print("\n📋 Test Results:\n")

for desc in test_descriptions:
    normalized = extract_merchant(desc)
    category = get_merchant_category(normalized)
    
    print(f"Original:   {desc}")
    print(f"Normalized: {normalized}")
    if category:
        print(f"Category:   {category}")
    print("-" * 80)

# Show statistics
print("\n📊 Merchant Database Statistics:\n")
all_merchants = get_all_predefined_merchants()
print(f"Total predefined merchants: {len(all_merchants)}")

# Count by category
from collections import Counter
category_counts = Counter(cat for _, cat in all_merchants)
print("\nMerchants by category:")
for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {cat}: {count}")

# Show some examples
print("\n🔍 Sample merchants:")
for merchant, category in all_merchants[:20]:
    print(f"  - {merchant} ({category})")
print(f"  ... and {len(all_merchants) - 20} more")
