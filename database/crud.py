"""CRUD helpers for database operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import Company, Contact, Plant, Subsidiary


# ── Company ───────────────────────────────────────────────────────────────────


def get_or_create_company(db: Session, name: str) -> tuple[Company, bool]:
    """Return (company, created) – created=True when a new row was inserted."""
    obj = db.query(Company).filter(func.lower(Company.name) == name.lower()).first()
    if obj:
        return obj, False
    obj = Company(name=name)
    db.add(obj)
    db.flush()
    return obj, True


def upsert_company(db: Session, name: str, **kwargs) -> Company:
    company, _ = get_or_create_company(db, name)
    for k, v in kwargs.items():
        if v is not None:
            setattr(company, k, v)
    db.flush()
    return company


def get_company(db: Session, company_id: int) -> Optional[Company]:
    return db.get(Company, company_id)


def list_companies(db: Session) -> list[Company]:
    return db.query(Company).order_by(Company.qualification_score.desc()).all()


def delete_company(db: Session, company_id: int) -> bool:
    obj = db.get(Company, company_id)
    if obj:
        db.delete(obj)
        db.flush()
        return True
    return False


# ── Subsidiary ────────────────────────────────────────────────────────────────


def add_subsidiary(db: Session, parent_id: int, **kwargs) -> Subsidiary:
    sub = Subsidiary(parent_id=parent_id, **kwargs)
    db.add(sub)
    db.flush()
    return sub


def list_subsidiaries(db: Session, parent_id: int) -> list[Subsidiary]:
    return db.query(Subsidiary).filter_by(parent_id=parent_id).all()


# ── Plant ─────────────────────────────────────────────────────────────────────


def add_plant(db: Session, company_id: int, **kwargs) -> Plant:
    plant = Plant(company_id=company_id, **kwargs)
    db.add(plant)
    db.flush()
    return plant


def list_plants(db: Session, company_id: Optional[int] = None) -> list[Plant]:
    q = db.query(Plant)
    if company_id is not None:
        q = q.filter_by(company_id=company_id)
    return q.order_by(Plant.company_id, Plant.city).all()


def delete_plant(db: Session, plant_id: int) -> bool:
    obj = db.get(Plant, plant_id)
    if obj:
        db.delete(obj)
        db.flush()
        return True
    return False


# ── Contact ───────────────────────────────────────────────────────────────────


def add_contact(db: Session, company_id: int, **kwargs) -> Contact:
    contact = Contact(company_id=company_id, **kwargs)
    db.add(contact)
    db.flush()
    return contact


def list_contacts(db: Session, company_id: Optional[int] = None) -> list[Contact]:
    q = db.query(Contact)
    if company_id is not None:
        q = q.filter_by(company_id=company_id)
    return q.order_by(Contact.company_id, Contact.seniority).all()


def delete_contact(db: Session, contact_id: int) -> bool:
    obj = db.get(Contact, contact_id)
    if obj:
        db.delete(obj)
        db.flush()
        return True
    return False


# ── Stats ─────────────────────────────────────────────────────────────────────


def get_stats(db: Session) -> dict:
    return {
        "companies": db.query(func.count(Company.id)).scalar() or 0,
        "plants": db.query(func.count(Plant.id)).scalar() or 0,
        "contacts": db.query(func.count(Contact.id)).scalar() or 0,
        "subsidiaries": db.query(func.count(Subsidiary.id)).scalar() or 0,
    }
