"""Run once to seed a demo officer login and a sample tender with a requirement checklist.

    python seed.py
"""
import time
from sqlalchemy import text
from app.database import Base, engine, SessionLocal
from app import models, auth

# Wait for database connection in cloud environments
for attempt in range(1, 31):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except Exception as e:
        print(f"Waiting for database to accept connections... attempt {attempt}/30")
        time.sleep(2)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    officer = db.query(models.User).filter(models.User.email == "officer@sih.gov.in").first()
    if not officer:
        officer = models.User(
            full_name="Procurement Officer",
            email="officer@sih.gov.in",
            hashed_password=auth.hash_password("ByteBusters@2026"),
            role=models.UserRole.admin,
        )
        db.add(officer)
        db.commit()
        db.refresh(officer)
        print(f"Seeded demo login -> officer@sih.gov.in / ByteBusters@2026 (id={officer.id})")

    tender = db.query(models.Tender).filter(models.Tender.reference_no == "SIH26100-DEMO").first()
    if not tender:
        tender = models.Tender(
            reference_no="SIH26100-DEMO",
            title="Supply of IT Equipment — Demo Tender",
            department="Ministry of Electronics & IT",
            theme="Smart Automation",
            created_by=officer.id,
        )
        db.add(tender)
        db.flush()

        demo_requirements = [
            ("GST Registration Certificate", "gst, goods and services tax, gstin", True),
            ("PAN Card", "pan, permanent account number", True),
            ("Company Registration Certificate", "certificate of incorporation, registrar of companies, cin", True),
            ("Experience Certificate", "experience certificate, prior work, completion certificate", True),
            ("EMD Proof (Earnest Money Deposit)", "emd, earnest money deposit, bid security", True),
            ("Technical Bid Document", "technical bid, technical proposal, specifications", True),
            ("Financial Bid Document", "financial bid, price bid, quotation, boq", True),
            ("Authorized Signatory Letter", "authorized signatory, power of attorney, authorization letter", False),
        ]
        for name, kws, mandatory in demo_requirements:
            db.add(models.Requirement(tender_id=tender.id, name=name, keywords=kws, mandatory=mandatory))

        db.commit()
        print("Seeded demo tender -> SIH26100-DEMO with 8 requirements")
except Exception as e:
    print(f"Seed notice: {e}")
    db.rollback()
finally:
    db.close()

print("Seed process completed.")
