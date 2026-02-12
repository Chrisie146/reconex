import sys
import io
import pandas as pd

sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

OPENING = 2101.35
BANK_CLOSING = 1177.79


def main():
    try:
        with open('Capitec.pdf', 'rb') as f:
            csv_bytes, _ = pdf_to_csv_bytes(f.read())
    except FileNotFoundError:
        print('Capitec.pdf not found in workspace root.')
        return

    df = pd.read_csv(io.BytesIO(csv_bytes))
    # Ensure numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

    parsed_sum = float(df['amount'].sum())
    system_closing = round(OPENING + parsed_sum, 2)
    diff = round(BANK_CLOSING - system_closing, 2)

    print(f'Opening: {OPENING:.2f}')
    print(f'Parsed transactions count: {len(df)}')
    print(f'Parsed transactions sum: {parsed_sum:.2f}')
    print(f'System closing (opening + parsed sum): {system_closing:.2f}')
    print(f'Bank closing (given): {BANK_CLOSING:.2f}')
    print(f'Difference (bank - system): {diff:.2f}')

    if abs(diff) < 0.01:
        print('Reconciled: parsed transactions match bank closing balance.')
        return

    print('\nTransactions that look like small fees (|amount| <= 5.00):')
    small_fees = df[df['amount'].abs() <= 5.00].sort_values('amount')
    print(small_fees[['date', 'description', 'amount']].to_string(index=False, max_rows=10))

    print('\nTop 20 largest absolute transactions:')
    print(df.reindex(df['amount'].abs().sort_values(ascending=False).index)[['date','description','amount']].head(20).to_string(index=False))


if __name__ == '__main__':
    main()
