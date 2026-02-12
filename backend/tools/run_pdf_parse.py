from services.pdf_parser import pdf_to_csv_bytes, ParserError
import sys
p = r'c:\Users\christopherm\statementbur_python\FNB_ASPIRE_CURRENT_ACCOUNT_1332.pdf'
try:
    with open(p,'rb') as f:
        b = f.read()
    csv_bytes, year = pdf_to_csv_bytes(b)
    print('---STATEMENT YEAR---', year)
    print(csv_bytes.decode('utf-8'))
except ParserError as e:
    print('PARSER ERROR:', e)
    sys.exit(1)
except Exception as e:
    import traceback
    print('ERROR:', e)
    traceback.print_exc()
    sys.exit(2)
