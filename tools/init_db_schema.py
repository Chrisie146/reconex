#!/usr/bin/env python
"""Initialize database schema - creates all tables defined in models.py"""

import sys
import os

# Change to root directory (where statement_analyzer.db is) and add backend to path
root_path = os.path.join(os.path.dirname(__file__), '..')
backend_path = os.path.join(root_path, 'backend')
os.chdir(root_path)
sys.path.insert(0, backend_path)

from models import engine, Base, init_db

print("Initializing database schema...")
print(f"DB: {Base.metadata.bind}")

try:
    init_db()
    print("✅ Database schema initialized successfully")
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTables in database: {tables}")
    
except Exception as e:
    print(f"❌ Failed to initialize database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
