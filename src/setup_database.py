#!/usr/bin/env python3
"""
Cash Logistics Database Setup Script
Generates realistic sample data for the Cash Logistics Agent demo.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
DB_PATH = Path(__file__).parent.parent / "data" / "cash_logistics.db"
NUM_STORES = 50
DAYS_OF_HISTORY = 90
REGIONS = ["North", "South", "East", "West"]

# Store name prefixes for realistic naming
STORE_PREFIXES = [
    "Downtown", "Eastside", "Westgate", "Central", "Harbor", "Valley",
    "Highland", "Riverside", "Lakeside", "Summit", "Crossroads", "Plaza",
    "Market", "Gateway", "Parkway", "Metro", "Village", "Square"
]

random.seed(42)  # For reproducibility


def create_tables(conn: sqlite3.Connection):
    """Create all database tables."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            store_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL,
            current_pickup_frequency INTEGER NOT NULL CHECK(current_pickup_frequency BETWEEN 1 AND 5),
            avg_daily_deposit REAL NOT NULL,
            smart_safe_enabled INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            deposit_date DATE NOT NULL,
            amount REAL NOT NULL,
            deposit_time TIME NOT NULL,
            FOREIGN KEY (store_id) REFERENCES stores(store_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_pickups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            scheduled_date DATE NOT NULL,
            scheduled_time TIME NOT NULL,
            actual_time TIME,
            status TEXT NOT NULL CHECK(status IN ('completed', 'missed', 'late')),
            FOREIGN KEY (store_id) REFERENCES stores(store_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carrier_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            total_stops INTEGER NOT NULL,
            cost_per_stop REAL NOT NULL,
            total_amount REAL NOT NULL
        )
    """)

    # Create indexes for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deposits_store_date ON deposits(store_id, deposit_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pickups_store_date ON scheduled_pickups(store_id, scheduled_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stores_region ON stores(region)")

    conn.commit()


def generate_stores(conn: sqlite3.Connection):
    """Generate 50 stores with specific scenarios built in."""
    cursor = conn.cursor()
    stores = []

    # Special scenario stores
    special_stores = {
        "342": {
            "name": "Westgate Commons #342",
            "region": "South",
            "pickup_freq": 5,
            "avg_deposit": 1800,  # Low volume, over-serviced
            "smart_safe": True
        },
        "127": {
            "name": "Downtown Flagship #127",
            "region": "North",
            "pickup_freq": 2,
            "avg_deposit": 8200,  # High volume, under-serviced (RISK)
            "smart_safe": False
        },
        "089": {
            "name": "Central Plaza #089",
            "region": "East",
            "pickup_freq": 3,
            "avg_deposit": 4500,  # Perfect match
            "smart_safe": True
        }
    }

    # Add special stores first
    for store_id, data in special_stores.items():
        stores.append((
            store_id,
            data["name"],
            data["region"],
            data["pickup_freq"],
            data["avg_deposit"],
            1 if data["smart_safe"] else 0
        ))

    # Generate remaining stores (47 more)
    used_ids = set(special_stores.keys())
    store_count = 0

    while store_count < 47:
        # Generate a 3-digit store ID
        store_id = f"{random.randint(1, 999):03d}"
        if store_id in used_ids:
            continue
        used_ids.add(store_id)

        prefix = random.choice(STORE_PREFIXES)
        region = random.choice(REGIONS)

        # Generate realistic deposit volumes (between $2000 and $7000 avg)
        avg_deposit = round(random.gauss(4500, 1200), 2)
        avg_deposit = max(2000, min(7000, avg_deposit))

        # Assign pickup frequency - generally correlate with volume but with some mismatches
        if avg_deposit < 3000:
            pickup_freq = random.choices([1, 2, 3], weights=[0.3, 0.5, 0.2])[0]
        elif avg_deposit < 5000:
            pickup_freq = random.choices([2, 3, 4], weights=[0.3, 0.5, 0.2])[0]
        else:
            pickup_freq = random.choices([3, 4, 5], weights=[0.2, 0.5, 0.3])[0]

        # Introduce some deliberate mismatches (about 15% of stores)
        if random.random() < 0.15:
            if avg_deposit > 5000 and pickup_freq > 3:
                pickup_freq = random.randint(1, 2)  # Under-serviced
            elif avg_deposit < 3500 and pickup_freq < 3:
                pickup_freq = random.randint(4, 5)  # Over-serviced

        smart_safe = random.random() < 0.4  # 40% have smart safes

        stores.append((
            store_id,
            f"{prefix} #{store_id}",
            region,
            pickup_freq,
            round(avg_deposit, 2),
            1 if smart_safe else 0
        ))
        store_count += 1

    cursor.executemany("""
        INSERT INTO stores (store_id, name, region, current_pickup_frequency, avg_daily_deposit, smart_safe_enabled)
        VALUES (?, ?, ?, ?, ?, ?)
    """, stores)

    conn.commit()
    return stores


def generate_deposits(conn: sqlite3.Connection, stores: list):
    """Generate 90 days of deposit history for all stores."""
    cursor = conn.cursor()
    deposits = []

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=DAYS_OF_HISTORY)

    for store_data in stores:
        store_id = store_data[0]
        avg_deposit = store_data[4]

        current_date = start_date
        while current_date <= end_date:
            # Weekend deposits are 40% higher
            is_weekend = current_date.weekday() >= 5
            base_amount = avg_deposit * 1.4 if is_weekend else avg_deposit

            # Add daily variation (+-20%)
            daily_variation = random.gauss(1.0, 0.15)
            daily_variation = max(0.7, min(1.3, daily_variation))
            amount = round(base_amount * daily_variation, 2)

            # Random deposit time between 6 PM and 10 PM
            hour = random.randint(18, 21)
            minute = random.randint(0, 59)
            deposit_time = f"{hour:02d}:{minute:02d}:00"

            deposits.append((
                store_id,
                current_date.isoformat(),
                amount,
                deposit_time
            ))

            current_date += timedelta(days=1)

    cursor.executemany("""
        INSERT INTO deposits (store_id, deposit_date, amount, deposit_time)
        VALUES (?, ?, ?, ?)
    """, deposits)

    conn.commit()
    print(f"Generated {len(deposits)} deposit records")


def generate_pickups(conn: sqlite3.Connection, stores: list):
    """Generate scheduled pickups based on store frequency, with some missed pickups in Q4."""
    cursor = conn.cursor()
    pickups = []

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=DAYS_OF_HISTORY)

    # Q4 date range for missed pickups (October - December)
    q4_start = datetime(end_date.year if end_date.month >= 10 else end_date.year - 1, 10, 1).date()
    q4_end = datetime(end_date.year if end_date.month >= 10 else end_date.year - 1, 12, 31).date()

    # Select 7 random store/date combinations for missed pickups
    missed_pickups = set()
    attempts = 0
    while len(missed_pickups) < 7 and attempts < 100:
        store = random.choice(stores)
        store_id = store[0]
        # Random date in Q4 that falls within our data range
        q4_day = q4_start + timedelta(days=random.randint(0, min((q4_end - q4_start).days, (end_date - q4_start).days)))
        if q4_day >= start_date and q4_day <= end_date:
            missed_pickups.add((store_id, q4_day.isoformat()))
        attempts += 1

    # Days of week for different pickup frequencies
    pickup_days_by_freq = {
        1: [1],  # Tuesday only
        2: [1, 4],  # Tuesday, Friday
        3: [0, 2, 4],  # Monday, Wednesday, Friday
        4: [0, 1, 3, 4],  # Mon, Tue, Thu, Fri
        5: [0, 1, 2, 3, 4]  # Mon-Fri
    }

    for store_data in stores:
        store_id = store_data[0]
        pickup_freq = store_data[3]
        pickup_days = pickup_days_by_freq[pickup_freq]

        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() in pickup_days:
                # Scheduled time between 9 AM and 2 PM
                scheduled_hour = random.randint(9, 13)
                scheduled_minute = random.choice([0, 15, 30, 45])
                scheduled_time = f"{scheduled_hour:02d}:{scheduled_minute:02d}:00"

                # Check if this is a missed pickup
                is_missed = (store_id, current_date.isoformat()) in missed_pickups

                if is_missed:
                    status = "missed"
                    actual_time = None
                elif random.random() < 0.08:  # 8% are late
                    status = "late"
                    late_minutes = random.randint(15, 90)
                    actual_hour = scheduled_hour + (scheduled_minute + late_minutes) // 60
                    actual_minute = (scheduled_minute + late_minutes) % 60
                    actual_time = f"{min(actual_hour, 23):02d}:{actual_minute:02d}:00"
                else:
                    status = "completed"
                    # Actual time within +-10 minutes of scheduled
                    delta_minutes = random.randint(-10, 10)
                    actual_hour = scheduled_hour + (scheduled_minute + delta_minutes) // 60
                    actual_minute = (scheduled_minute + delta_minutes) % 60
                    if actual_minute < 0:
                        actual_hour -= 1
                        actual_minute += 60
                    actual_time = f"{max(8, min(actual_hour, 17)):02d}:{actual_minute:02d}:00"

                pickups.append((
                    store_id,
                    current_date.isoformat(),
                    scheduled_time,
                    actual_time,
                    status
                ))

            current_date += timedelta(days=1)

    cursor.executemany("""
        INSERT INTO scheduled_pickups (store_id, scheduled_date, scheduled_time, actual_time, status)
        VALUES (?, ?, ?, ?, ?)
    """, pickups)

    conn.commit()
    print(f"Generated {len(pickups)} pickup records")

    # Count missed pickups
    cursor.execute("SELECT COUNT(*) FROM scheduled_pickups WHERE status = 'missed'")
    missed_count = cursor.fetchone()[0]
    print(f"  - Missed pickups: {missed_count}")


def generate_invoices(conn: sqlite3.Connection):
    """Generate carrier invoices for the last 3 months."""
    cursor = conn.cursor()

    end_date = datetime.now().date()

    invoices = []
    for months_ago in range(3, 0, -1):
        month_date = end_date - timedelta(days=30 * months_ago)
        month_str = month_date.strftime("%Y-%m")

        # Count stops for that month
        cursor.execute("""
            SELECT COUNT(*) FROM scheduled_pickups
            WHERE strftime('%Y-%m', scheduled_date) = ?
            AND status IN ('completed', 'late')
        """, (month_str,))
        total_stops = cursor.fetchone()[0]

        # If no data for that month, estimate based on stores
        if total_stops == 0:
            total_stops = random.randint(400, 600)

        cost_per_stop = round(random.uniform(18.50, 22.50), 2)
        total_amount = round(total_stops * cost_per_stop, 2)

        invoices.append((
            month_str,
            total_stops,
            cost_per_stop,
            total_amount
        ))

    cursor.executemany("""
        INSERT INTO carrier_invoices (month, total_stops, cost_per_stop, total_amount)
        VALUES (?, ?, ?, ?)
    """, invoices)

    conn.commit()
    print(f"Generated {len(invoices)} invoice records")


def main():
    """Main function to set up the database."""
    print(f"Setting up Cash Logistics database at {DB_PATH}")

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Removed existing database")

    # Connect and create tables
    conn = sqlite3.connect(DB_PATH)

    print("\nCreating tables...")
    create_tables(conn)

    print("\nGenerating stores...")
    stores = generate_stores(conn)
    print(f"Generated {len(stores)} stores")

    print("\nGenerating deposits (90 days of history)...")
    generate_deposits(conn, stores)

    print("\nGenerating scheduled pickups...")
    generate_pickups(conn, stores)

    print("\nGenerating carrier invoices...")
    generate_invoices(conn)

    # Print summary
    print("\n" + "="*50)
    print("DATABASE SETUP COMPLETE")
    print("="*50)

    cursor = conn.cursor()

    print("\nTable counts:")
    for table in ["stores", "deposits", "scheduled_pickups", "carrier_invoices"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} records")

    print("\nSpecial scenario stores:")
    cursor.execute("""
        SELECT store_id, name, avg_daily_deposit, current_pickup_frequency
        FROM stores WHERE store_id IN ('342', '127', '089')
        ORDER BY store_id
    """)
    for row in cursor.fetchall():
        print(f"  #{row[0]}: {row[1]}")
        print(f"    Avg deposit: ${row[2]:,.2f}/day, Pickup freq: {row[3]}x/week")

    print("\nRegion distribution:")
    cursor.execute("""
        SELECT region, COUNT(*) as count
        FROM stores
        GROUP BY region
        ORDER BY region
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} stores")

    conn.close()
    print(f"\nDatabase saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
