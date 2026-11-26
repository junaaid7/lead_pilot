import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Business, Inspection, Lead, SearchJob


def make_business(**overrides):
    data = dict(
        name="Apex Properties",
        country="AE",
        city="Dubai",
        niche="REAL_ESTATE",
        source="google_places",
        canonical_domain="apex.example",
        place_id="place_1",
    )
    data.update(overrides)
    return Business(**data)


def make_job(**overrides):
    data = dict(
        user_id=uuid.uuid4(),
        country="AE",
        niche="REAL_ESTATE",
        city_ids=[292223],
        lead_count=50,
        filters={},
        status="QUEUED",
    )
    data.update(overrides)
    return SearchJob(**data)


def test_duplicate_canonical_domain_is_rejected(session):
    session.add(make_business())
    session.commit()

    session.add(make_business(place_id="place_2"))  # domain wohi, place_id alag
    with pytest.raises(IntegrityError) as exc:
        session.flush()
    assert "uq_businesses_canonical_domain" in str(exc.value)
    session.rollback()


def test_duplicate_place_id_is_rejected(session):
    session.add(make_business())
    session.commit()

    session.add(make_business(canonical_domain="other.example"))  # place_id wohi
    with pytest.raises(IntegrityError) as exc:
        session.flush()
    assert "uq_businesses_place_id" in str(exc.value)
    session.rollback()


def test_businesses_without_domain_are_allowed(session):
    # NULL, UNIQUE ko nahi todta: bina website ki do businesses theek hain
    session.add(make_business(canonical_domain=None, place_id="p1"))
    session.add(make_business(canonical_domain=None, place_id="p2"))
    session.flush()


def test_lead_count_must_be_between_1_and_200(session):
    session.add(make_job(lead_count=500))
    with pytest.raises(IntegrityError) as exc:
        session.flush()
    assert "ck_search_jobs_lead_count_range" in str(exc.value)
    session.rollback()


def test_accepted_count_cannot_exceed_lead_count(session):
    session.add(make_job(lead_count=50, accepted_count=51))
    with pytest.raises(IntegrityError) as exc:
        session.flush()
    assert "ck_search_jobs_accepted_lte_requested" in str(exc.value)
    session.rollback()


def test_same_business_cannot_be_twice_in_one_job(session):
    business = make_business()
    job = make_job()
    session.add_all([business, job])
    session.flush()

    inspection = Inspection(business_id=business.id, status="OK")
    session.add(inspection)
    session.flush()

    session.add(
        Lead(job_id=job.id, business_id=business.id, inspection_id=inspection.id)
    )
    session.commit()

    session.add(
        Lead(job_id=job.id, business_id=business.id, inspection_id=inspection.id)
    )
    with pytest.raises(IntegrityError) as exc:
        session.flush()
    assert "uq_leads_job_business" in str(exc.value)
    session.rollback()