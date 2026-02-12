# Direct Invoice Upload Feature

## Overview
Users can now upload invoices directly from the transactions table without any modal complexity. When a transaction has no linked invoice, they can click "+ Upload Invoice" to add one instantly.

## How It Works

### 1. **Uploading an Invoice**
- Click the **"+ Upload Invoice"** button in the Invoice column of any transaction
- A modal opens showing:
  - Transaction date
  - Transaction amount
  - Description (for reference)

### 2. **Upload Methods**
Choose one:
- **Drag & Drop** - Drag a PDF file directly onto the upload area
- **Click to Browse** - Click "Select File" to open file browser
- Supported format: **PDF only**
- Maximum file size: **20MB**

### 3. **Automatic Processing**
After uploading, the system automatically:
1. Extracts invoice metadata (supplier name, invoice date, total amount, VAT, invoice number)
2. Creates an invoice record in the database
3. Attempts to match it to transactions
4. Links it to the current transaction (by amount matching)

### 4. **Success Feedback**
- Shows a green checkmark when upload completes
- Transaction table updates automatically
- Invoice now appears in the Invoice column

## Features

### Visual Indicators
- **"+ Upload Invoice"** - Transaction has no invoice linked
- **Blue badge with number** - Transaction has linked invoice(s)
  - Click to view invoice details

### Smart Matching
- Invoices are automatically matched to transactions by **total amount**
- One transaction can have multiple invoices (rare, but supported)
- Shows count of matched invoices

### Invoice Details Viewer
Click on the blue invoice badge to see:
- Supplier name
- Invoice date
- Invoice number
- Total amount & VAT
- Download PDF link

## Error Handling

If upload fails:
- Clear error message explains what went wrong
- Common issues:
  - "Only PDF files are allowed" - File must be PDF format
  - "File is too large" - Reduce file size below 20MB
  - "Failed to extract key fields" - PDF doesn't contain readable invoice data

Try again or check your PDF file format.

## Technical Details

**Backend Endpoints:**
- `POST /invoice/upload_file_auto` - Upload and auto-extract invoice
- `GET /invoices?session_id=...` - List all invoices for session
- `GET /invoice/download` - Download invoice PDF

**Frontend Components:**
- `InvoiceUploadModal.tsx` - Upload modal dialog
- `TransactionsTable.tsx` - Integrated invoice column with upload capability

## Tips

1. **Batch Uploads** - Upload invoices for one transaction at a time, or use external tools to batch process if you have many
2. **Update Immediately** - After upload, the table refreshes automatically with the new invoice link
3. **View Later** - Click the invoice badge anytime to view full details or download
