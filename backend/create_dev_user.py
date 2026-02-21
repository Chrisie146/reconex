#!/usr/bin/env python
"""
Development User Creation Script
Creates a test user account for local development
Usage: python create_dev_user.py
"""

import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from models import init_db, get_db, User, Client, engine, Base
from auth import get_password_hash

def create_dev_user(email: str = "dev@example.com", password: str = "dev123456", name: str = "Test Developer"):
    """Create a development user account"""
    
    # Initialize database tables
    print("\n[*] Initializing database...")
    Base.metadata.create_all(bind=engine)
    init_db()
    print("[✓] Database initialized")
    
    # Get database session
    SessionLocal = __import__('models').SessionLocal
    db = SessionLocal()
    
    try:
        # Check if user already exists
        print(f"\n[*] Checking if user {email} already exists...")
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            print(f"[!] User {email} already exists!")
            print(f"    Email: {existing_user.email}")
            print(f"    Name: {existing_user.full_name}")
            print(f"    Created: {existing_user.created_at}")
            db.close()
            return
        
        # Create new user
        print(f"[*] Creating user: {email}")
        hashed_password = get_password_hash(password)
        
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            is_active=True,
            is_superuser=False,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.flush()  # Flush to get the user ID without committing
        
        # Create default client for the user
        print(f"[*] Creating default client...")
        default_client = Client(
            user_id=new_user.id,
            name="My First Client"
        )
        
        db.add(default_client)
        db.commit()
        
        print("\n[✓] Development user created successfully!")
        print(f"\n{'='*60}")
        print("  LOGIN CREDENTIALS")
        print(f"{'='*60}")
        print(f"  Email:    {email}")
        print(f"  Password: {password}")
        print(f"  API URL:  http://localhost:8000")
        print(f"  Docs:     http://localhost:8000/docs")
        print(f"{'='*60}\n")
        print("Login Steps:")
        print("  1. Open http://localhost:8000/docs in your browser")
        print("  2. Click 'Authorize' and enter email and password above")
        print("  3. Try POST /auth/login or use the frontend\n")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Check if custom email/password provided as arguments
    email = sys.argv[1] if len(sys.argv) > 1 else "dev@example.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "dev123456"
    name = sys.argv[3] if len(sys.argv) > 3 else "Test Developer"
    
    create_dev_user(email=email, password=password, name=name)
