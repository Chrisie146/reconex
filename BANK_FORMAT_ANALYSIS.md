# Multi-Bank Statement Format Analysis

## Standard Bank Format

**Structure**: Space-separated columns, multi-line transactions

**Column Headers** (Row 4):
```
Page Details Service Fee Debit Credit Date Balance
```

**Format Details**:
- **Page**: Page number (10, 11, 12, etc.)
- **Details**: Description spans 1-2 lines sometimes
- **Service Fee**: Always 0.00 or 19.00
- **Debit**: Negative amounts (outflow) - shows as negative value
- **Credit**: Positive amounts (inflow) - shows as positive value
- **Date**: YYYYMMDD format (20240222, 20240223, etc.)
- **Balance**: Running balance after transaction

**Transaction Pattern**:
```
Page Details Service Fee Debit Credit Date Balance
10 ELECTRONIC BANKING TRANSFER TO 0.00 -92.71 0.00 20240222 6,536,806.66
FHP ERROR ACCOUNT FIXED
10 ELECTRONIC BANKING PAYMENT TO 0.00 -13,026.61 0.00 20240223 6,523,780.05
SAGEF NETCASH       B0WD310:12
```

**Challenges**:
- Merchant name can span multiple lines (e.g., "ELECTRONIC BANKING TRANSFER TO" followed by "FHP ERROR ACCOUNT FIXED")
- Service Fee column sometimes has value (19.00) which affects logic
- Need to parse: Debit (negative) OR Credit (positive) for amount

---

## ABSA Bank Format

**Status**: Scanned PDF (images) - requires OCR processing

**Implication**:
- Cannot extract text directly with pdfplumber
- Must use OCR service (pytesseract + pdf2image conversion)
- Need to implement OCR preprocessing (deskew, contrast enhancement)
- Performance impact: slower processing

---

## Implementation Plan

### Phase 1: Bank Detection
1. Add `bank_source` field to Transaction model
2. Create BankDetector class to identify format:
   - Check column headers
   - Sample first few rows for patterns
   - Return: ('standard_bank', 'absa', 'capitec', 'unknown')

### Phase 2: Bank Adapters
1. **StandardBankAdapter**
   - Parse columns: Page, Details, Service Fee, Debit, Credit, Date, Balance
   - Handle multi-line descriptions
   - Combine Debit/Credit into single Amount column (Debit = negative, Credit = positive)
   - Convert date format YYYYMMDD → YYYY-MM-DD

2. **ABSAAdapter** (with OCR)
   - Convert PDF to images
   - Apply OCR
   - Parse resulting format
   - TBD: Need to see actual OCR'd ABSA format

3. **CapitecAdapter**
   - TBD: Need sample data

### Phase 3: Parser Updates
1. Update `pdf_to_csv_bytes()` to:
   - Detect bank format
   - Apply appropriate adapter
   - Return normalized CSV

2. Update `validate_csv()` to:
   - Accept normalized output from adapters
   - Store bank_source metadata

### Phase 4: Database & API
1. Add `bank_source` to Transaction model
2. Add API endpoint: `GET /api/detect-bank` (for UI preview)
3. Add upload parameter: `bank_source` (allow override)

---

## Questions

1. **ABSA PDF**: Is this expected to be scanned/OCR'd, or is this a sample? Do you have native ABSA CSV/PDF exports?
2. **Capitec**: Do you have a Capitec sample to add to this analysis?
3. **API Design**: Should bank detection be automatic or manual selection?
4. **Backwards Compatibility**: Should we maintain generic CSV support for unknown banks?
