OCR Endpoints

1) Save OCR Regions
POST /ocr/regions?session_id=<session_id>

Payload example:
{
  "page": 1,
  "date_region": { "x": 0.05, "y": 0.2, "w": 0.15, "h": 0.6 },
  "description_region": { "x": 0.2, "y": 0.2, "w": 0.45, "h": 0.6 },
  "amount_region": { "x": 0.7, "y": 0.2, "w": 0.2, "h": 0.6 },
  "amount_type": "single"
}

Coordinates must be relative (0..1) to support different resolutions.

2) Run OCR
POST /ocr/extract?session_id=<session_id>

Body: Upload the scanned PDF file as form file field `file`.
The server will use previously saved regions to crop the target page and run OCR.

Response includes parsed `rows`, `warnings`, and counts per region.
