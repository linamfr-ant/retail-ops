#!/usr/bin/env python3
"""Initialize and seed the database."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.seed_data import seed_database


def main():
    """Initialize the database with seed data."""
    print("🗄️  Initializing logistics database...")
    seed_database()
    print("\n✅ Database ready at: data/logistics.db")


if __name__ == "__main__":
    main()
