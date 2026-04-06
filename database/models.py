"""SQLAlchemy ORM models for the Lead Intelligence Platform."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    """Top-level company record (parent or subsidiary)."""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255))
    description = Column(Text)
    industry = Column(String(255))
    sub_industry = Column(String(255))
    size_range = Column(String(50))          # e.g. "1,000-5,000"
    employee_count = Column(Integer)
    annual_revenue = Column(String(50))      # human-readable string
    headquarters_city = Column(String(100))
    headquarters_country = Column(String(100))
    headquarters_address = Column(String(255))
    founded_year = Column(Integer)
    stock_ticker = Column(String(20))
    linkedin_url = Column(String(500))
    parent_company = Column(String(255))     # name of parent if subsidiary
    qualification_score = Column(Float, default=0.0)
    qualification_tier = Column(String(20))  # A / B / C / D
    research_status = Column(String(30), default="pending")  # pending/researching/done/error
    research_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plants = relationship("Plant", back_populates="company", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    subsidiaries = relationship(
        "Subsidiary", back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r}>"


class Subsidiary(Base):
    """A subsidiary or related entity of a parent company."""

    __tablename__ = "subsidiaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    domain = Column(String(255))
    country = Column(String(100))
    industry = Column(String(255))
    relationship_type = Column(String(50))  # subsidiary / division / brand / JV
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Company", back_populates="subsidiaries")

    def __repr__(self) -> str:
        return f"<Subsidiary id={self.id} name={self.name!r}>"


class Plant(Base):
    """A physical production site, facility, or office location."""

    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    site_type = Column(String(50))           # manufacturing / warehouse / HQ / office / R&D / lab
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    employee_count = Column(Integer)
    area_sqft = Column(Integer)              # facility size
    products_produced = Column(Text)         # CSV of products made here
    certifications = Column(Text)            # ISO, HACCP, etc.
    year_established = Column(Integer)
    status = Column(String(30), default="active")  # active / closed / planned
    source_url = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="plants")
    contacts = relationship("Contact", back_populates="plant")

    def __repr__(self) -> str:
        return f"<Plant id={self.id} name={self.name!r} city={self.city!r}>"


class Contact(Base):
    """A professional contact at a company or plant."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    plant_id = Column(Integer, ForeignKey("plants.id"), nullable=True)
    full_name = Column(String(255), nullable=False)
    title = Column(String(255))
    department = Column(String(100))
    seniority = Column(String(30))           # C-level / VP / Director / Manager / Individual
    email = Column(String(255))
    phone = Column(String(50))
    linkedin_url = Column(String(500))
    location = Column(String(100))
    source = Column(String(100))             # website / linkedin / hunter / manual
    confidence_score = Column(Float, default=0.5)  # 0.0 – 1.0
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")
    plant = relationship("Plant", back_populates="contacts")

    def __repr__(self) -> str:
        return f"<Contact id={self.id} name={self.full_name!r}>"
