"""
Migration: Add delivery_status column to nfts table.

This migration adds the 'delivery_status' column that tracks whether an NFT
has been successfully transferred to the fan's wallet.

Values:
  - 'delivered'      → NFT has been transferred to the fan
  - 'pending_optin'  → NFT is minted but fan hasn't opted in via Pera Wallet yet
  - 'failed'         → Transfer attempt failed

Run from the backend/ directory:
    python scripts/migrate_add_delivery_status.py
"""
import os
import sys
import sqlite3

# Add backend/ to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


def get_db_path() -> str:
    """Extract the SQLite file path from the database URL."""
    url = settings.database_url
    # sqlite:///./data/sticker_platform.db → ./data/sticker_platform.db
    path = url.replace("sqlite:///", "")
    if not os.path.isabs(path):
        # Resolve relative to backend/ directory
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    return path


def migrate():
    db_path = get_db_path()
    print(f"📂 Database: {db_path}")

    if not os.path.exists(db_path):
        print("⚠️  Database file not found. It will be created on next server start")
        print("   with the new column already included. No migration needed!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(nfts)")
    columns = [row[1] for row in cursor.fetchall()]

    if "delivery_status" in columns:
        print("✅ Column 'delivery_status' already exists in 'nfts' table. Nothing to do.")
        conn.close()
        return

    print("🔧 Adding 'delivery_status' column to 'nfts' table...")

    # Add the column with default 'delivered' (existing NFTs were all delivered)
    cursor.execute("""
        ALTER TABLE nfts
        ADD COLUMN delivery_status VARCHAR(20) NOT NULL DEFAULT 'delivered'
    """)

    # Verify
    cursor.execute("PRAGMA table_info(nfts)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "delivery_status" in columns, "Migration failed: column not added"

    # Check how many rows were updated
    cursor.execute("SELECT COUNT(*) FROM nfts")
    total = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    print(f"✅ Migration complete!")
    print(f"   - Column 'delivery_status' added to 'nfts' table")
    print(f"   - {total} existing NFT(s) set to 'delivered' (default)")
    print(f"   - New NFTs will get 'pending_optin' when fan hasn't opted in")


if __name__ == "__main__":
    migrate()
