import io
from typing import Dict, List, Tuple, Any

from PIL import Image
import pytesseract

from pdf2image import convert_from_bytes

from .parser import parse_date, parse_amount, ParserError


def _group_words_into_rows(words: List[Dict[str, Any]], y_tol: int = 12) -> List[Dict[str, Any]]:
    """Group OCR word dicts (with 'top' and 'left') into rows by vertical proximity."""
    if not words:
        return []
    # Sort by top then left
    words_sorted = sorted(words, key=lambda w: (w['top'], w['left']))
    rows: List[Dict[str, Any]] = []
    current_row = {'y': words_sorted[0]['top'], 'words': []}

    for w in words_sorted:
        if abs(w['top'] - current_row['y']) <= y_tol:
            current_row['words'].append(w)
            # update running y to median-ish
            current_row['y'] = int((current_row['y'] + w['top']) / 2)
        else:
            # finish row
            rows.append(current_row)
            current_row = {'y': w['top'], 'words': [w]}

    rows.append(current_row)

    # Convert to nicer structure: text joined left->right, average y
    out_rows: List[Dict[str, Any]] = []
    for r in rows:
        words_in_row = sorted(r['words'], key=lambda x: x['left'])
        text = ' '.join([w['text'] for w in words_in_row if w.get('text') and w.get('text').strip()])
        avg_y = int(sum(w['top'] for w in words_in_row) / max(1, len(words_in_row)))
        out_rows.append({'y': avg_y, 'text': text, 'words': words_in_row})

    return out_rows


def _ocr_crop(image: Image.Image, crop_box: Tuple[int, int, int, int], lang: str = 'eng') -> List[Dict[str, Any]]:
    """Run pytesseract.image_to_data on a cropped region and return words with positions relative to full page."""
    left, top, right, bottom = crop_box
    crop = image.crop((left, top, right, bottom))
    # run image_to_data
    data = pytesseract.image_to_data(crop, lang=lang, output_type=pytesseract.Output.DICT)
    words = []
    n = len(data.get('text', []))
    for i in range(n):
        txt = data['text'][i]
        if not txt or str(txt).strip() == '':
            continue
        try:
            conf = float(data.get('conf', ["-1"])[i])
        except Exception:
            conf = -1.0
        w = int(data.get('width', [0])[i])
        h = int(data.get('height', [0])[i])
        l = int(data.get('left', [0])[i]) + left
        t = int(data.get('top', [0])[i]) + top
        words.append({'text': str(txt).strip(), 'left': l, 'top': t, 'width': w, 'height': h, 'conf': conf})
    return words


def run_extraction(pdf_bytes: bytes, regions: Dict[str, Any], page: int = 1, dpi: int = 300, lang: str = 'eng') -> Dict[str, Any]:
    """
    Run OCR on specified regions for a single page and return aligned rows and warnings.

    regions: Dict containing keys like 'date_region','description_region','amount_region' (or debit/credit)
    Each region: {x,y,w,h} relative coordinates (0..1)
    page: 1-indexed page number
    """
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=dpi)
    except Exception as e:
        raise ParserError(f"Failed to convert PDF to images: {e}")

    if page < 1 or page > len(pages):
        raise ParserError(f"Requested page {page} out of range (1..{len(pages)})")

    page_img = pages[page - 1].convert('RGB')
    W, H = page_img.size

    # Prepare list of region crops
    crops = {}
    for key in ('date_region', 'description_region', 'amount_region', 'debit_region', 'credit_region'):
        r = regions.get(key)
        if not r:
            continue
        # validate relative coords
        x = max(0.0, min(1.0, float(r.get('x', 0))))
        y = max(0.0, min(1.0, float(r.get('y', 0))))
        w = max(0.0, min(1.0, float(r.get('w', 0))))
        h = max(0.0, min(1.0, float(r.get('h', 0))))
        left = int(x * W)
        top = int(y * H)
        right = int((x + w) * W)
        bottom = int((y + h) * H)
        # clamp
        left = max(0, min(left, W - 1))
        top = max(0, min(top, H - 1))
        right = max(left + 1, min(right, W))
        bottom = max(top + 1, min(bottom, H))
        crops[key] = (left, top, right, bottom)

    # OCR each crop into words
    region_words = {}
    for k, box in crops.items():
        try:
            words = _ocr_crop(page_img, box, lang=lang)
        except Exception:
            words = []
        region_words[k] = words

    # Group words into rows per region
    region_rows = {k: _group_words_into_rows(v) for k, v in region_words.items()}

    # Attempt alignment across rows using y positions
    # We'll build a master row list by using the description region (preferred) or date
    master_key = 'description_region' if 'description_region' in region_rows else next(iter(region_rows.keys()))
    master_rows = region_rows.get(master_key, [])

    parsed_rows = []
    warnings = []

    for mr in master_rows:
        row_y = mr['y']
        row = {'y': row_y, 'description': mr['text'], 'date': None, 'amount': None, 'issues': []}

        # Find closest date row
        if 'date_region' in region_rows:
            candidates = region_rows['date_region']
            closest = min(candidates, key=lambda c: abs(c['y'] - row_y)) if candidates else None
            if closest and abs(closest['y'] - row_y) <= 20:
                row['date_raw'] = closest['text']
                parsed_date = parse_date(closest['text'])
                if parsed_date:
                    row['date'] = parsed_date.isoformat()
                else:
                    row['issues'].append('date_parse_failed')
            else:
                row['issues'].append('date_missing')

        # Amount handling
        if 'amount_region' in region_rows:
            candidates = region_rows['amount_region']
            closest = min(candidates, key=lambda c: abs(c['y'] - row_y)) if candidates else None
            if closest and abs(closest['y'] - row_y) <= 20:
                row['amount_raw'] = closest['text']
                amt = parse_amount(closest['text'])
                if amt is None:
                    row['issues'].append('amount_parse_failed')
                else:
                    row['amount'] = amt
            else:
                row['issues'].append('amount_missing')

        # Debit/Credit separate columns
        if 'debit_region' in region_rows or 'credit_region' in region_rows:
            # prefer credit/debit parsing if present
            debit_cand = None
            credit_cand = None
            if 'debit_region' in region_rows:
                dlist = region_rows['debit_region']
                if dlist:
                    debit_cand = min(dlist, key=lambda c: abs(c['y'] - row_y))
            if 'credit_region' in region_rows:
                clist = region_rows['credit_region']
                if clist:
                    credit_cand = min(clist, key=lambda c: abs(c['y'] - row_y))

            val = None
            if debit_cand and abs(debit_cand['y'] - row_y) <= 20:
                val = parse_amount(debit_cand['text'])
                if val is not None:
                    val = -abs(val)
                else:
                    row['issues'].append('debit_parse_failed')
            if credit_cand and abs(credit_cand['y'] - row_y) <= 20:
                val2 = parse_amount(credit_cand['text'])
                if val2 is not None:
                    val = val2
                else:
                    row['issues'].append('credit_parse_failed')

            if val is not None:
                row['amount'] = val
            else:
                # If amount already set from amount_region, keep it
                if 'amount' not in row or row['amount'] is None:
                    row.setdefault('issues', []).append('amount_missing')

        parsed_rows.append(row)

    # Basic mismatch detection: if date rows count differs markedly from master rows
    if 'date_region' in region_rows and abs(len(region_rows['date_region']) - len(master_rows)) > max(1, int(len(master_rows) * 0.15)):
        warnings.append('row_count_mismatch_between_date_and_description')
    if ('amount_region' in region_rows) and abs(len(region_rows['amount_region']) - len(master_rows)) > max(1, int(len(master_rows) * 0.15)):
        warnings.append('row_count_mismatch_between_amount_and_description')

    return {'rows': parsed_rows, 'warnings': warnings, 'counts': {k: len(v) for k, v in region_rows.items()}}
