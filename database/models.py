"""SQLAlchemy models for armored carrier logistics database."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Location(Base):
    """Retail store locations requiring armored carrier pickup."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    store_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    city = Column(String(50))
    state = Column(String(2))
    region = Column(String(50))  # e.g., "Northeast", "Southwest"
    avg_daily_cash_volume = Column(Float)  # Expected daily cash in dollars
    risk_tier = Column(String(10))  # "high", "medium", "low"

    # Relationships
    deposits = relationship("Deposit", back_populates="location")
    pickup_schedules = relationship("PickupSchedule", back_populates="location")


class Carrier(Base):
    """Armored carrier companies."""

    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    base_pickup_cost = Column(Float)  # Base cost per pickup
    per_mile_cost = Column(Float)
    overtime_rate_multiplier = Column(Float, default=1.5)
    max_daily_stops = Column(Integer)

    # Relationships
    pickup_schedules = relationship("PickupSchedule", back_populates="carrier")


class PickupSchedule(Base):
    """Scheduled pickups - which carrier visits which location and when."""

    __tablename__ = "pickup_schedules"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False)
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    scheduled_time = Column(String(5))  # HH:MM format
    route_sequence = Column(Integer)  # Order in daily route

    # Relationships
    location = relationship("Location", back_populates="pickup_schedules")
    carrier = relationship("Carrier", back_populates="pickup_schedules")
    costs = relationship("PickupCost", back_populates="schedule")

    __table_args__ = (
        Index("idx_schedule_location_day", "location_id", "day_of_week"),
    )


class Deposit(Base):
    """Cash deposits made at each location."""

    __tablename__ = "deposits"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    amount = Column(Float, nullable=False)
    deposit_timestamp = Column(DateTime, nullable=False)
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    deposit_type = Column(String(20))  # "daily_close", "mid_day", "weekend"

    # Relationships
    location = relationship("Location", back_populates="deposits")

    __table_args__ = (
        Index("idx_deposit_location_date", "location_id", "deposit_timestamp"),
    )


class PickupCost(Base):
    """Actual costs incurred for each scheduled pickup."""

    __tablename__ = "pickup_costs"

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey("pickup_schedules.id"), nullable=False)
    pickup_date = Column(DateTime, nullable=False)
    base_cost = Column(Float)
    fuel_surcharge = Column(Float)
    overtime_cost = Column(Float, default=0.0)
    insurance_cost = Column(Float)
    total_cost = Column(Float)
    cash_collected = Column(Float)  # Actual cash picked up

    # Relationships
    schedule = relationship("PickupSchedule", back_populates="costs")

    __table_args__ = (
        Index("idx_cost_date", "pickup_date"),
    )
