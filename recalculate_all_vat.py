"""
Manually recalculate VAT for all enabled sessions
Run this from the statementbur_python directory: python recalculate_all_vat.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models import SessionLocal, SessionVATConfig
from services.vat_service import VATService

def recalculate_all():
    db = SessionLocal()
    vat_service = VATService()
    
    try:
        # Get all sessions with VAT enabled
        configs = db.query(SessionVATConfig).filter(
            SessionVATConfig.vat_enabled == 1
        ).all()
        
        print(f"Found {len(configs)} sessions with VAT enabled")
        
        for config in configs:
            session_id = config.session_id
            print(f"\nRecalculating VAT for session: {session_id[:8]}...")
            
            success, message, stats = vat_service.recalculate_all_transactions(session_id)
            
            if success:
                print(f"  ✓ Success: {stats.get('total_recalculated', 0)} transactions updated")
                print(f"  ✓ With VAT: {stats.get('with_vat', 0)}, Without VAT: {stats.get('without_vat', 0)}")
            else:
                print(f"  ✗ Failed: {message}")
        
        print(f"\n{'='*60}")
        print("VAT recalculation complete!")
        print("Refresh your browser to see the updated VAT amounts.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    recalculate_all()
