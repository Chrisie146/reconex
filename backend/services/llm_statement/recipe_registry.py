"""Shared, versionable recipes for explicit-column text statements.

Recipes contain header geometry and date formats, never statement values or
customer text. A recipe is promoted only after exact replay of a validated model
extraction. Every hit is parsed from the new document and validated again.
"""
import hashlib
import json
import os
from pathlib import Path
import re
from datetime import datetime
from decimal import Decimal

from .ingest import DATE_ROW_PATTERN
from .redaction import _redact_line

VERSION = 1
LABELS = {
    'date': ('date', 'transaction date'),
    'description': ('description', 'transaction description', 'details'),
    'category': ('category',),
    'credit': ('money in', 'credit', 'credits', 'deposits', 'paid in'),
    'debit': ('money out', 'debit', 'debits', 'withdrawals', 'paid out'),
    'amount': ('amount',),
    'fee': ('fee', 'fees'),
    'balance': ('balance', 'running balance'),
}
DATE_FORMATS = ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%m/%d/%Y')
MONEY = re.compile(r'^(?P<sign>[+-]?)(?:R\s*)?(?P<n>(?:\d{1,3}(?:[ ,]\d{3})+|\d+)\.\d{2})(?P<mark>\s*(?:Dr|Cr))?$', re.I)


class RecipeMiss(ValueError):
    pass


def words(line):
    result = []
    for span in line.word_spans:
        match = re.fullmatch(r'x=(-?\d+(?:\.\d+)?):(.*)', span)
        if not match:
            raise RecipeMiss('missing_word_geometry')
        result.append((float(match[1]), match[2]))
    return sorted(result)


def header(line):
    """Accept only complete known table labels, not arbitrary document text."""
    tokens = words(line)
    normal = [re.sub(r'[^a-z ]', '', t.lower()) for _, t in tokens]
    fields = []
    i = 0
    while i < len(tokens):
        matches = []
        for field, alternatives in LABELS.items():
            for label in alternatives:
                size = len(label.split())
                if ' '.join(normal[i:i + size]) == label:
                    matches.append((size, field, label))
        if not matches:
            return None
        size, field, label = max(matches)
        fields.append((field, tokens[i][0], label))
        i += size
    names = [f[0] for f in fields]
    if len(set(names)) != len(names) or not {'date', 'description', 'balance'} <= set(names):
        return None
    if not ({'credit', 'debit'} <= set(names) or 'amount' in names):
        return None
    if names[:2] != ['date', 'description'] or names[-1] != 'balance':
        return None
    return fields


def layout_shape(assessment):
    shapes = []
    for page in assessment.pages:
        for line in page.lines:
            fields = header(line)
            if fields:
                shape = {'width': round(page.width, 1), 'height': round(page.height, 1),
                         'columns': [[name, round(x, 1), label] for name, x, label in fields]}
                if shape not in shapes:
                    shapes.append(shape)
    # Different header shapes need separate parsing semantics; don't generalise.
    if len(shapes) != 1:
        raise RecipeMiss('unsupported_or_changed_headers')
    return shapes[0]


def money(text, require_sign=False):
    match = MONEY.fullmatch(text.strip())
    if not match:
        raise RecipeMiss('unsupported_money')
    sign, number, marker = match['sign'], match['n'], (match['mark'] or '').strip().lower()
    if require_sign and not sign and not marker:
        raise RecipeMiss('ambiguous_direction')
    if (sign == '-' and marker == 'cr') or (sign == '+' and marker == 'dr'):
        raise RecipeMiss('conflicting_direction')
    value = Decimal(number.replace(' ', '').replace(',', ''))
    return -value if sign == '-' or marker == 'dr' else value


def anchors(assessment, fmt):
    found = {k: set() for k in ('opening_balance', 'closing_balance', 'statement_period_start', 'statement_period_end')}
    labels = {
        'opening_balance': r'opening\s+balance', 'closing_balance': r'closing\s+balance',
        'statement_period_start': r'from\s+date', 'statement_period_end': r'to\s+date',
    }
    currency = set()
    for page in assessment.pages:
        for line in page.lines:
            for key, label in labels.items():
                match = re.search(r'\b' + label + r'\s*:\s*(.*)', line.text, re.I)
                if not match:
                    continue
                tail = match[1]
                if key.endswith('balance'):
                    # Stop at the next metadata label if two fields share a line.
                    tail = re.split(r'\s+[A-Za-z][A-Za-z ]+:', tail)[0].strip()
                    found[key].add(format(money(tail), '.2f'))
                    if re.match(r'[+-]?R\s*\d', tail):
                        currency.add('ZAR')
                else:
                    try:
                        found[key].add(datetime.strptime(tail.split()[0], fmt).date().isoformat())
                    except ValueError as exc:
                        raise RecipeMiss('unsupported_period') from exc
            match = re.fullmatch(r'Currency\s*:\s*([A-Z]{3})', line.text.strip(), re.I)
            if match:
                currency.add(match[1].upper())
    if any(len(v) != 1 for v in found.values()) or len(currency) != 1:
        raise RecipeMiss('missing_or_conflicting_anchors')
    return {**{k: next(iter(v)) for k, v in found.items()}, 'currency': next(iter(currency))}


def extract_recipe(assessment, recipe):
    if set(recipe) != {'version', 'shape', 'date_format'} or recipe['version'] != VERSION:
        raise RecipeMiss('recipe_version')
    if recipe['date_format'] not in DATE_FORMATS or layout_shape(assessment) != recipe['shape']:
        raise RecipeMiss('layout_changed')
    fmt = recipe['date_format']
    extraction = {'document_type': 'bank_statement', 'bank_name': None, 'account_type': None,
                  'account_number_last4': None, **anchors(assessment, fmt),
                  'processed_pages': assessment.expected_pages, 'transaction_pages': [],
                  'transactions': [], 'extraction_notes': []}
    columns = recipe['shape']['columns']
    # Header-based bands are deliberately conservative. Replay rejects recipes
    # where typography, wrapping, or long amounts cross these boundaries.
    starts = [x - (12 if name in {'credit', 'debit', 'amount', 'fee', 'balance'} else 3)
              for name, x, _ in columns]
    for page in assessment.pages:
        active = False
        page_rows = 0
        candidate_indexes = [
            index for index, item in enumerate(page.lines)
            if (match := DATE_ROW_PATTERN.search(item.text)) and item.text[match.end():].strip()
        ]
        last_candidate = max(candidate_indexes, default=-1)
        for line_index, line in enumerate(page.lines):
            if header(line):
                active = True
                continue
            match = DATE_ROW_PATTERN.search(line.text)
            candidate = bool(match and line.text[match.end():].strip())
            if not active:
                if candidate:
                    raise RecipeMiss('dated_row_outside_table')
                continue
            if line_index > last_candidate:
                # Statement footers vary and are outside the transaction table.
                # Coverage still has to match the independent dated-row count.
                continue
            cells = {name: [] for name, _, _ in columns}
            for x, text in words(line):
                positions = [i for i, start in enumerate(starts) if x >= start]
                if positions:
                    cells[columns[max(positions)][0]].append(text)
            cells = {name: ' '.join(tokens) for name, tokens in cells.items()}
            if not candidate:
                # Do not silently skip undated monetary rows or continuations.
                if re.search(r'\d[.,]\d{2}\b', line.text):
                    raise RecipeMiss('undated_numeric_row')
                if cells['description'] and not re.search(r'\b(page|includes|bank|document)\b', line.text, re.I):
                    raise RecipeMiss('wrapped_or_unknown_row')
                continue
            try:
                day = datetime.strptime(cells['date'], fmt).date().isoformat()
            except ValueError as exc:
                raise RecipeMiss('unsupported_row_date') from exc
            if not cells['description']:
                raise RecipeMiss('missing_description')
            if 'amount' in cells:
                amount = money(cells['amount'], require_sign=True)
                direction = 'debit' if amount < 0 else 'credit'
            else:
                if bool(cells['credit']) == bool(cells['debit']):
                    raise RecipeMiss('ambiguous_amount_columns')
                direction = 'credit' if cells['credit'] else 'debit'
                amount = money(cells[direction])
                if direction == 'credit' and amount < 0:
                    raise RecipeMiss('contradictory_credit')
            fee = money(cells['fee'], require_sign=True) if cells.get('fee') else Decimal('0.00')
            prefix = day + ' '
            description, _ = _redact_line(prefix + cells['description'], {}, [0])
            row = {'date': day, 'value_date': None, 'description': description[len(prefix):],
                   'amount': format(abs(amount), '.2f'), 'direction': direction,
                   'additional_fee': format(fee, '.2f'), 'balance_after': format(money(cells['balance']), '.2f'),
                   'source_page': page.number, 'source_row_ordinal': page_rows + 1,
                   'source_bbox': {'x0': line.x0, 'top': line.top, 'x1': line.x1, 'bottom': line.bottom}}
            extraction['transactions'].append(row)
            page_rows += 1
        if page_rows != page.candidate_transaction_rows:
            raise RecipeMiss('row_coverage')
        if page_rows:
            extraction['transaction_pages'].append(page.number)
    if not extraction['transactions']:
        raise RecipeMiss('no_transactions')
    return extraction


def learn_recipe(assessment, reference, validator):
    """No generated code: learn only a whitelisted, replay-proven recipe."""
    if not validator.validate(reference, assessment.expected_pages).passed:
        return None
    try:
        shape = layout_shape(assessment)
    except RecipeMiss:
        return None
    matches = []
    financial = ('date', 'value_date', 'amount', 'direction', 'additional_fee', 'balance_after',
                 'source_page', 'source_row_ordinal')
    for fmt in DATE_FORMATS:
        recipe = {'version': VERSION, 'shape': shape, 'date_format': fmt}
        try:
            local = extract_recipe(assessment, recipe)
        except (RecipeMiss, ValueError):
            continue
        if not validator.validate(local, assessment.expected_pages).passed:
            continue
        if any(local[k] != reference[k] for k in ('opening_balance', 'closing_balance', 'currency',
                   'statement_period_start', 'statement_period_end', 'processed_pages', 'transaction_pages')):
            continue
        actual, expected = local['transactions'], reference['transactions']
        if len(actual) != len(expected):
            continue
        if any(any(a[k] != b[k] for k in financial) or
               ' '.join(a['description'].split()) != ' '.join(b['description'].split())
               for a, b in zip(actual, expected)):
            continue
        matches.append(recipe)
    return matches[0] if len(matches) == 1 else None


class CodeRecipeRegistry:
    """Versionable, application-wide recipe files containing no customer data."""

    def __init__(self, directory):
        self.directory = Path(directory)

    def fingerprint(self, assessment):
        shape = json.dumps(layout_shape(assessment), sort_keys=True)
        # This must remain stable across customers, hosts and deployments so a
        # reviewed recipe committed to the application works for every user.
        return hashlib.sha256(shape.encode()).hexdigest()

    def load(self, assessment):
        try:
            path = self.directory / f'{self.fingerprint(assessment)}.json'
            if not path.is_file() or path.stat().st_size > 16384:
                return None
            return json.loads(path.read_text(encoding='utf-8'))
        except (RecipeMiss, OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def save(self, assessment, recipe):
        try:
            # Validate the exact whitelist before writing anything into source.
            if set(recipe) != {'version', 'shape', 'date_format'}:
                return False
            payload = json.dumps(recipe, indent=2, sort_keys=True) + '\n'
            if len(payload.encode()) > 16384:
                return False
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f'{self.fingerprint(assessment)}.json'
            temporary = path.with_suffix('.tmp')
            temporary.write_text(payload, encoding='utf-8')
            os.replace(temporary, path)
            return True
        except (RecipeMiss, OSError, ValueError, TypeError):
            return False
