"""Run once to seed a demo officer login and a sample tender with a requirement checklist.

    python seed.py
"""
from app.database import Base, engine, SessionLocal
from app import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(models.User).filter(models.User.email == "officer@sih.gov.in").first():
    officer = models.User(
        full_name="Procurement Officer",
        email="officer@sih.gov.in",
        hashed_password=auth.hash_password("ByteBusters@2026"),
        role=models.UserRole.admin,
    )
    db.add(officer)
    print("Seeded demo login -> officer@sih.gov.in / ByteBusters@2026")

if not db.query(models.Tender).filter(models.Tender.reference_no == "SIH26100-DEMO").first():
    tender = models.Tender(
        reference_no="SIH26100-DEMO",
        title="Supply of IT Equipment — Demo Tender",
        department="Ministry of Electronics & IT",
        theme="Smart Automation",
        created_by=1,
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

    print("Seeded demo tender -> SIH26100-DEMO with 8 requirements")

db.commit()
db.close()
print("Done.")
