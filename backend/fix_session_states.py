"""
Fix missing SessionState records for existing transactions
"""

import sqlite3
from datetime import datetime

def fix_session_states(db_path="backend/statement_analyzer.db"):
    """Create SessionState records for sessions that don't have them"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Find all session_ids that have transactions but no SessionState
    cursor.execute("""
        SELECT DISTINCT t.session_id
        FROM transactions t
        LEFT JOIN session_states ss ON t.session_id = ss.session_id
        WHERE ss.session_id IS NULL
    """)
    
    missing_sessions = [row[0] for row in cursor.fetchall()]
    
    if not missing_sessions:
        print("✓ No missing SessionState records found")
        conn.close()
        return
    
    print(f"Found {len(missing_sessions)} sessions without SessionState records")
    print("Creating records...")
    
    for session_id in missing_sessions:
        # Generate a friendly name from session_id prefix
        friendly_name = f"Statement {session_id[:8]}"
        created_at = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO session_states (session_id, friendly_name, created_at)
            VALUES (?, ?, ?)
        """, (session_id, friendly_name, created_at))
        
        print(f"  ✓ Created SessionState for {session_id[:8]}... → '{friendly_name}'")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Fixed {len(missing_sessions)} SessionState records!")

if __name__ == "__main__":
    fix_session_states()
