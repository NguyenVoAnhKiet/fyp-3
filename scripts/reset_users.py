#!/usr/bin/env python3
"""
Reset users and face references from the database.

This script deletes all users and face references while preserving
attendance records and recognition events for historical tracking.

Usage:
    PYTHONPATH=src python scripts/reset_users.py

The script reads DATABASE_PATH from .env file.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from attendance_system.core.db import Database, DatabaseConfig


def main():
    # Load .env
    load_dotenv()
    
    # Get database path
    db_path = os.getenv("DATABASE_PATH", "attendance.db")
    
    print(f"Database path: {db_path}")
    print("\nThis will delete:")
    print("  - All users (users table)")
    print("  - All face references (face_references table)")
    print("\nPreserved:")
    print("  - Attendance records (for historical tracking)")
    print("  - Recognition events (for historical tracking)")
    
    # Confirm
    confirmation = input("\nType 'YES' to confirm deletion: ").strip()
    if confirmation != "YES":
        print("Cancelled.")
        return
    
    # Connect to database
    try:
        config = DatabaseConfig(path=Path(db_path))
        db = Database(config)
        
        with db.session() as conn:
            # Delete face references first (FK constraint)
            conn.execute("DELETE FROM face_references")
            deleted_faces = conn.total_changes
            
            # Delete users
            conn.execute("DELETE FROM users")
            deleted_users = conn.total_changes - deleted_faces
            
            print(f"\n✓ Deleted {deleted_users} users")
            print(f"✓ Deleted {deleted_faces} face references")
            print("✓ Done!")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
