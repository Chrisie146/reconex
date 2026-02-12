"""Test the export functions directly"""
import sys
sys.path.insert(0, '.')

from services.summary import ExcelExporter
from models import SessionLocal, Transaction

db = SessionLocal()

# Get first session ID
sessions = db.query(Transaction.session_id).distinct().limit(1).all()
if sessions:
    session_id = sessions[0][0]
    print(f"Testing exports for session: {session_id}")
    
    # Test old export
    try:
        output = ExcelExporter.export_all_categories_monthly(session_id, db)
        print("✓ export_all_categories_monthly: Success!")
        print(f"  Output size: {len(output.getvalue())} bytes")
    except Exception as e:
        print(f"✗ export_all_categories_monthly failed:")
        import traceback
        print(traceback.format_exc())
    
    # Test new accountant export
    try:
        output = ExcelExporter.export_for_accountant(session_id, db)
        print("✓ export_for_accountant: Success!")
        print(f"  Output size: {len(output.getvalue())} bytes")
    except Exception as e:
        print(f"✗ export_for_accountant failed:")
        import traceback
        print(traceback.format_exc())
else:
    print("No sessions found in database")

db.close()
