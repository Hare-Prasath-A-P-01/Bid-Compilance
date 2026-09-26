from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_options = {"pool_pre_ping": True}
if not is_sqlite:
    engine_options.update({
        "pool_size": 15,
        "max_overflow": 25,
        "pool_recycle": 1800,  # recycle stale connections after 30 mins
        "pool_timeout": 30,
    })
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



def ensure_schema():
    """Add Tier 1 fields to an existing local database."""
    inspector = inspect(engine)
    additions = {
        "users": {
            "department": "VARCHAR(255)",
        },
        "tenders": {
            "description": "TEXT",
            "status": "VARCHAR(20) DEFAULT 'Draft' NOT NULL",
            "submission_deadline": "DATETIME",
        },
        "bids": {
            "submission_status": "VARCHAR(20) DEFAULT 'Draft' NOT NULL",
            "submitted_version": "INTEGER DEFAULT 0 NOT NULL",
        },
        "requirements": {
            "aliases": "VARCHAR(1000)",
            "critical": "BOOLEAN DEFAULT 0",
            "weight": "FLOAT DEFAULT 1.0",
        },
        "bid_documents": {
            "content_hash": "VARCHAR(64)",
            "matched_keywords": "VARCHAR(1000)",
            "extraction_method": "VARCHAR(30)",
            "text_quality": "FLOAT",
            "expiry_date": "DATETIME",
            "review_status": "VARCHAR(20) DEFAULT 'pending' NOT NULL",
            "review_comment": "VARCHAR(1000)",
            "reviewed_by": "INTEGER",
            "reviewed_at": "DATETIME",
            "assigned_reviewer_id": "INTEGER",
            "review_due_at": "DATETIME",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
