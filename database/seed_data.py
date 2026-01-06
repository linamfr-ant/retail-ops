"""Seed database with realistic mock data for demo scenarios."""

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import Location, Carrier, PickupSchedule, Deposit, PickupCost
from .connection import init_db, get_session

# Seed for reproducibility
random.seed(42)

# Demo scenarios we want to highlight:
# 1. High-volume stores with infrequent pickups (cash sitting risk)
# 2. Low-volume stores with too frequent pickups (over-servicing)
# 3. Deposit patterns misaligned with pickup schedules
# 4. Route consolidation opportunities (nearby stores, different days)

LOCATIONS_DATA = [
    # HIGH VOLUME - should have frequent pickups
    {"store_code": "NE-001", "name": "Boston Downtown", "city": "Boston", "state": "MA", "region": "Northeast", "avg_daily_cash_volume": 45000, "risk_tier": "high"},
    {"store_code": "NE-002", "name": "Manhattan Midtown", "city": "New York", "state": "NY", "region": "Northeast", "avg_daily_cash_volume": 62000, "risk_tier": "high"},
    {"store_code": "NE-003", "name": "Brooklyn Heights", "city": "Brooklyn", "state": "NY", "region": "Northeast", "avg_daily_cash_volume": 38000, "risk_tier": "high"},

    # MEDIUM VOLUME
    {"store_code": "NE-004", "name": "Hartford Central", "city": "Hartford", "state": "CT", "region": "Northeast", "avg_daily_cash_volume": 22000, "risk_tier": "medium"},
    {"store_code": "NE-005", "name": "Providence Mall", "city": "Providence", "state": "RI", "region": "Northeast", "avg_daily_cash_volume": 18000, "risk_tier": "medium"},
    {"store_code": "SE-001", "name": "Atlanta Perimeter", "city": "Atlanta", "state": "GA", "region": "Southeast", "avg_daily_cash_volume": 28000, "risk_tier": "medium"},
    {"store_code": "SE-002", "name": "Miami Beach", "city": "Miami", "state": "FL", "region": "Southeast", "avg_daily_cash_volume": 35000, "risk_tier": "medium"},
    {"store_code": "SE-003", "name": "Orlando Tourist", "city": "Orlando", "state": "FL", "region": "Southeast", "avg_daily_cash_volume": 42000, "risk_tier": "high"},

    # LOW VOLUME - candidates for reduced pickups
    {"store_code": "MW-001", "name": "Cleveland Suburb", "city": "Cleveland", "state": "OH", "region": "Midwest", "avg_daily_cash_volume": 8000, "risk_tier": "low"},
    {"store_code": "MW-002", "name": "Detroit Outlet", "city": "Detroit", "state": "MI", "region": "Midwest", "avg_daily_cash_volume": 6500, "risk_tier": "low"},
    {"store_code": "MW-003", "name": "Columbus Center", "city": "Columbus", "state": "OH", "region": "Midwest", "avg_daily_cash_volume": 12000, "risk_tier": "low"},
    {"store_code": "SW-001", "name": "Phoenix Downtown", "city": "Phoenix", "state": "AZ", "region": "Southwest", "avg_daily_cash_volume": 15000, "risk_tier": "medium"},
    {"store_code": "SW-002", "name": "Tucson Mall", "city": "Tucson", "state": "AZ", "region": "Southwest", "avg_daily_cash_volume": 9000, "risk_tier": "low"},
    {"store_code": "WE-001", "name": "LA Downtown", "city": "Los Angeles", "state": "CA", "region": "West", "avg_daily_cash_volume": 55000, "risk_tier": "high"},
    {"store_code": "WE-002", "name": "San Diego Harbor", "city": "San Diego", "state": "CA", "region": "West", "avg_daily_cash_volume": 32000, "risk_tier": "medium"},
]

CARRIERS_DATA = [
    {"name": "Brinks", "base_pickup_cost": 125.0, "per_mile_cost": 2.50, "overtime_rate_multiplier": 1.5, "max_daily_stops": 12},
    {"name": "Loomis", "base_pickup_cost": 115.0, "per_mile_cost": 2.75, "overtime_rate_multiplier": 1.5, "max_daily_stops": 10},
    {"name": "Garda", "base_pickup_cost": 135.0, "per_mile_cost": 2.25, "overtime_rate_multiplier": 1.75, "max_daily_stops": 14},
]

# Pickup schedule patterns (intentionally suboptimal for demo)
# Format: (store_code, carrier_name, days_of_week, time)
SCHEDULE_PATTERNS = [
    # HIGH VOLUME but only picked up 2x/week - PROBLEM
    ("NE-001", "Brinks", [1, 4], "10:00"),  # Boston - only Tue/Fri
    ("NE-002", "Brinks", [0, 2, 4], "09:00"),  # Manhattan - Mon/Wed/Fri (ok)
    ("NE-003", "Brinks", [2], "11:00"),  # Brooklyn - only Wed - PROBLEM

    # MEDIUM VOLUME with appropriate schedules
    ("NE-004", "Loomis", [1, 4], "14:00"),  # Hartford
    ("NE-005", "Loomis", [1, 4], "15:00"),  # Providence - same days, could consolidate
    ("SE-001", "Garda", [0, 3], "10:00"),  # Atlanta
    ("SE-002", "Garda", [1, 4], "11:00"),  # Miami
    ("SE-003", "Garda", [0, 2, 4], "09:00"),  # Orlando - high volume, good frequency

    # LOW VOLUME but picked up too often - OVER-SERVICING
    ("MW-001", "Loomis", [0, 2, 4], "13:00"),  # Cleveland - 3x/week for low volume
    ("MW-002", "Loomis", [0, 2, 4], "14:00"),  # Detroit - 3x/week for low volume
    ("MW-003", "Loomis", [1, 3], "15:00"),  # Columbus
    ("SW-001", "Garda", [1, 4], "10:00"),  # Phoenix
    ("SW-002", "Garda", [0, 2, 4], "11:00"),  # Tucson - over-serviced
    ("WE-001", "Brinks", [0, 1, 2, 3, 4], "08:00"),  # LA - daily (appropriate)
    ("WE-002", "Brinks", [1, 3], "09:00"),  # San Diego
]


def seed_locations(session: Session) -> dict[str, Location]:
    """Create location records."""
    locations = {}
    for data in LOCATIONS_DATA:
        loc = Location(
            store_code=data["store_code"],
            name=data["name"],
            address=f"{random.randint(100, 9999)} Main St",
            city=data["city"],
            state=data["state"],
            region=data["region"],
            avg_daily_cash_volume=data["avg_daily_cash_volume"],
            risk_tier=data["risk_tier"],
        )
        session.add(loc)
        locations[data["store_code"]] = loc
    session.flush()
    return locations


def seed_carriers(session: Session) -> dict[str, Carrier]:
    """Create carrier records."""
    carriers = {}
    for data in CARRIERS_DATA:
        carrier = Carrier(**data)
        session.add(carrier)
        carriers[data["name"]] = carrier
    session.flush()
    return carriers


def seed_schedules(
    session: Session,
    locations: dict[str, Location],
    carriers: dict[str, Carrier],
) -> list[PickupSchedule]:
    """Create pickup schedule records."""
    schedules = []
    for store_code, carrier_name, days, time in SCHEDULE_PATTERNS:
        location = locations[store_code]
        carrier = carriers[carrier_name]
        for seq, day in enumerate(days):
            schedule = PickupSchedule(
                location_id=location.id,
                carrier_id=carrier.id,
                day_of_week=day,
                scheduled_time=time,
                route_sequence=seq + 1,
            )
            session.add(schedule)
            schedules.append(schedule)
    session.flush()
    return schedules


def seed_deposits(session: Session, locations: dict[str, Location]):
    """Create 90 days of deposit history with realistic patterns."""
    end_date = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=90)

    for store_code, location in locations.items():
        base_amount = location.avg_daily_cash_volume
        current_date = start_date

        while current_date <= end_date:
            day_of_week = current_date.weekday()

            # Weekend patterns (higher volume Fri-Sun for retail)
            if day_of_week == 4:  # Friday
                multiplier = random.uniform(1.3, 1.6)
            elif day_of_week == 5:  # Saturday
                multiplier = random.uniform(1.4, 1.8)
            elif day_of_week == 6:  # Sunday
                multiplier = random.uniform(1.1, 1.4)
            elif day_of_week == 0:  # Monday (post-weekend)
                multiplier = random.uniform(0.7, 0.9)
            else:
                multiplier = random.uniform(0.85, 1.15)

            # Add some randomness
            amount = base_amount * multiplier * random.uniform(0.9, 1.1)

            deposit = Deposit(
                location_id=location.id,
                amount=round(amount, 2),
                deposit_timestamp=current_date,
                day_of_week=day_of_week,
                deposit_type="daily_close" if day_of_week < 5 else "weekend",
            )
            session.add(deposit)

            current_date += timedelta(days=1)

    session.flush()


def seed_pickup_costs(session: Session, schedules: list[PickupSchedule], locations: dict[str, Location]):
    """Create 90 days of pickup cost history with MISSED PICKUPS for demo."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    # === MISSED PICKUP SCENARIOS (last 7 days) ===
    # These stores will have missed pickups to trigger alerts
    missed_pickup_config = {
        # Brooklyn Heights (NE-003): HIGH volume ($38K/day), only 1 pickup/week
        # MISSED: Last scheduled pickup was skipped (5 days of cash sitting)
        "NE-003": {"skip_last_n_pickups": 1, "reason": "Carrier vehicle breakdown"},

        # Manhattan Midtown (NE-002): HIGH volume ($62K/day)
        # MISSED: Last 2 pickups skipped (major cash accumulation)
        "NE-002": {"skip_last_n_pickups": 2, "reason": "Holiday staffing shortage"},

        # Miami Beach (SE-002): MEDIUM volume ($35K/day)
        # MISSED: Last pickup skipped (weekend cash not collected)
        "SE-002": {"skip_last_n_pickups": 1, "reason": "Route rescheduled"},

        # LA Downtown (WE-001): HIGH volume ($55K/day), daily pickups
        # MISSED: Last 3 pickups skipped (3 days no pickup for daily store!)
        "WE-001": {"skip_last_n_pickups": 3, "reason": "Security incident"},

        # Orlando Tourist (SE-003): HIGH volume ($42K/day)
        # MISSED: Last pickup skipped
        "SE-003": {"skip_last_n_pickups": 1, "reason": "Weather delay"},
    }

    # Build lookup: location_id -> store_code
    location_id_to_code = {}
    for code, loc in locations.items():
        location_id_to_code[loc.id] = code

    # Track pickups per location to know which to skip
    location_pickup_dates = {code: [] for code in locations.keys()}

    # First pass: collect all pickup dates per location
    for schedule in schedules:
        store_code = location_id_to_code[schedule.location_id]
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() == schedule.day_of_week:
                location_pickup_dates[store_code].append(current_date)
            current_date += timedelta(days=1)

    # Sort pickup dates
    for code in location_pickup_dates:
        location_pickup_dates[code].sort()

    # Determine which dates to skip for missed pickup stores
    skip_dates = {}
    for store_code, config in missed_pickup_config.items():
        if store_code in location_pickup_dates:
            pickups = location_pickup_dates[store_code]
            n_skip = config["skip_last_n_pickups"]
            # Skip the last N pickup dates
            dates_to_skip = pickups[-n_skip:] if len(pickups) >= n_skip else pickups
            skip_dates[store_code] = set(dates_to_skip)

    # Second pass: create pickup costs, skipping missed ones
    for schedule in schedules:
        carrier = schedule.carrier
        location = schedule.location
        store_code = location_id_to_code[location.id]
        current_date = start_date

        while current_date <= end_date:
            # Only create cost records for scheduled days
            if current_date.weekday() == schedule.day_of_week:

                # Check if this pickup should be SKIPPED (missed)
                if store_code in skip_dates and current_date in skip_dates[store_code]:
                    # SKIP this pickup - it's a missed pickup!
                    current_date += timedelta(days=1)
                    continue

                base = carrier.base_pickup_cost
                fuel = base * random.uniform(0.08, 0.15)  # 8-15% fuel surcharge
                insurance = base * 0.05  # 5% insurance

                # Overtime for late pickups (simulate some)
                overtime = 0.0
                if random.random() < 0.15:  # 15% chance of overtime
                    overtime = base * 0.25 * carrier.overtime_rate_multiplier

                total = base + fuel + insurance + overtime

                # Cash collected based on deposits since last pickup
                cash_collected = location.avg_daily_cash_volume * random.uniform(1.5, 3.5)

                cost = PickupCost(
                    schedule_id=schedule.id,
                    pickup_date=current_date,
                    base_cost=round(base, 2),
                    fuel_surcharge=round(fuel, 2),
                    overtime_cost=round(overtime, 2),
                    insurance_cost=round(insurance, 2),
                    total_cost=round(total, 2),
                    cash_collected=round(cash_collected, 2),
                )
                session.add(cost)

            current_date += timedelta(days=1)

    session.flush()

    # Print missed pickup summary
    print("\n  MISSED PICKUPS CREATED FOR DEMO:")
    for store_code, config in missed_pickup_config.items():
        if store_code in skip_dates:
            loc = locations[store_code]
            days_missed = len(skip_dates[store_code])
            cash_at_risk = loc.avg_daily_cash_volume * days_missed
            print(f"    - {loc.name} ({store_code}): {days_missed} missed, ~${cash_at_risk:,.0f} at risk")


def seed_database():
    """Initialize and seed the entire database."""
    print("Initializing database...")
    init_db()

    session = get_session()

    try:
        print("Seeding locations...")
        locations = seed_locations(session)

        print("Seeding carriers...")
        carriers = seed_carriers(session)

        print("Seeding pickup schedules...")
        schedules = seed_schedules(session, locations, carriers)

        print("Seeding deposits (90 days)...")
        seed_deposits(session, locations)

        print("Seeding pickup costs (90 days)...")
        seed_pickup_costs(session, schedules, locations)

        session.commit()
        print("Database seeded successfully!")
        print(f"  - {len(locations)} locations")
        print(f"  - {len(carriers)} carriers")
        print(f"  - {len(schedules)} pickup schedules")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
