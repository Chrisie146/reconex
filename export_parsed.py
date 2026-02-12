import sys, io, pandas as pd
sys.path.insert(0, 'backend')
from backend.services.pdf_parser import pdf_to_csv_bytes

csv_bytes, _ = pdf_to_csv_bytes(open('Capitec.pdf', 'rb').read())
df = pd.read_csv(io.BytesIO(csv_bytes))
df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)

# Export to CSV for manual review
df.to_csv('parsed_transactions.csv', index=False)
print('Exported parsed_transactions.csv')

# Also create a summary by date
print('\n=== SUMMARY BY DATE ===')
df_sorted = df.sort_values('date')
daily = df_sorted.groupby('date')['amount'].agg(['sum', 'count'])
daily.columns = ['net_change', 'transaction_count']
print(daily)

# Show which amounts are outliers (to spot missing large transactions)
print('\n\n=== ALL TRANSACTIONS (sorted by date, then amount) ===')
for date in sorted(df['date'].unique()):
    day_txns = df[df['date'] == date].sort_values('amount')
    total = day_txns['amount'].sum()
    print(f"\n{date} ({len(day_txns)} txns, net {total:+.2f}):")
    for idx, row in day_txns.iterrows():
        print(f"  {row['amount']:>10.2f} {row['description'][:55]}")
