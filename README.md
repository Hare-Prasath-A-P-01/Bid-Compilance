# AI Bid Compliance Checker — Byte Busters (SIH 2026)

An AI-assisted system that checks tender bid documents against a procurement
checklist automatically — extracting text from PDFs/scans, matching each
document to the requirement it satisfies, flagging expired or suspicious
documents, and producing a compliance score and risk rating for every bid.

Built for Smart India Hackathon by Byte Busters.

## What it does

- **Tender setup** — a procurement officer creates a tender and defines the
  document checklist (e.g. GST Certificate, PAN Card, EMD Proof, Technical
  Bid, Financial Bid), each with keywords used for matching.
- **Bid intake** — bidders' documents are uploaded per bid (PDF, image, or
  text). Scanned PDFs and images are OCR'd automatically.
- **Automated compliance check** — a rule-based engine matches each document
  to the requirement it satisfies, flags likely issues (expired validity
  dates, blank/corrupted scans, unmatched documents), and rolls everything up
  into a 0–100 compliance score and a Low / Medium / High risk rating.
- **Optional LLM assist** — if `ANTHROPIC_API_KEY` is set, flagged documents
  get a one-line, plain-English explanation from Claude on top of the
  rule-based flag. The app works fully without a key; this is additive.
- **Audit trail** — every upload and bid action is logged and viewable per
  bid, for transparency during evaluation.

## Tech stack

| Layer      | Technology |
|------------|------------|
| Frontend   | React 18 + Vite, plain CSS (no UI framework) |
| Backend    | FastAPI (Python), SQLAlchemy ORM |
| Database   | PostgreSQL (SQLite fallback for local dev without Docker) |
| Document processing | pdfplumber (PDF text), pytesseract + Tesseract OCR (scans/images) |
| Compliance logic | Keyword-based classifier + heuristic issue detection |
| Auth       | JWT (python-jose) + bcrypt password hashing |
| LLM (optional) | Anthropic API (`claude-sonnet-4-6`) for human-readable flag explanations |

## Running it — Docker (recommended)

Requires Docker + Docker Compose.

```bash
export SECRET_KEY="replace-with-a-long-random-secret"
docker compose up --build
```

This starts a health-checked Postgres service, the backend, and the frontend.
Open **http://localhost:4173**. Set `SECRET_KEY` to a unique value before
starting; production mode rejects the local development secret.

To create the demo login and tender once after the services are running:

```bash
docker compose exec backend python seed.py
```

Demo login: `officer@sih.gov.in` / `ByteBusters@2026`

For a database backup from a running Docker stack, use PowerShell:

```powershell
.\scripts\backup.ps1
```

The repository CI workflow runs backend tests and the frontend production build
on every push and pull request. Docker services expose `/api/health` and
`/api/ready` for health and readiness checks.

To enable the optional LLM explanations, export a key before starting:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

## Running it — manual (no Docker)

**Backend** (uses SQLite automatically if `DATABASE_URL` isn't set):

```bash
cd backend
# Use Python 3.11+ locally; on Windows, Python 3.13 worked reliably for this project
py -3.13 -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python seed.py            # creates demo login + demo tender
python -m uvicorn app.main:app --reload --port 8000
```

OCR requires the Tesseract binary on your machine (`apt install tesseract-ocr`
on Debian/Ubuntu, `brew install tesseract` on macOS). Without it, image-based
documents just extract no text rather than crashing — PDF text layers and
plain text files still work fine.

**Frontend** (separate terminal):

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api` to the backend on 8000.

## Project structure

```
byte-busters/
  backend/
    app/
      main.py              FastAPI app + router registration
      models.py             SQLAlchemy tables
      schemas.py            Pydantic request/response models
      auth.py                JWT + password hashing
      routers/
        auth.py              register / login
        tenders.py           create tenders + requirement checklists
        bids.py               register bids per tender
        documents.py         upload/delete documents, triggers auto-evaluation
        compliance.py         compliance report endpoint
      services/
        document_processor.py  PDF/OCR text extraction
        compliance_engine.py   keyword matching, issue detection, scoring
        llm_service.py          optional Claude-powered explanations
    seed.py                 demo login + demo tender
    requirements.txt
    Dockerfile
  frontend/
    src/
      pages/                Login, Dashboard, NewTender, TenderDetail, BidDetail
      components/           Shell (sidebar layout), RiskBadge
      context/AuthContext.jsx
      api/client.js
    Dockerfile              nginx serving the built app + reverse-proxying /api
  docker-compose.yml
```

## How the compliance score is calculated

1. Every uploaded document's text is scored against every requirement's
   keyword list; the best match above a confidence threshold assigns the
   document to that requirement.
2. Heuristics scan matched documents for red flags — dates that read as
   expired, explicit "expired" mentions, near-empty extracted text (a sign of
   a blank or corrupted scan).
3. A document that matches a requirement with no issues is **Matched**; a
   match with issues is **Mismatched** (needs manual review); a requirement
   with no matching document at all is **Missing**.
4. Score = (mandatory requirements matched ÷ total mandatory requirements) ×
   100, minus a penalty per mismatched document. Risk is **Low** at ≥85 with
   no flags, **Medium** at ≥60, otherwise **High**.

This is a transparent, explainable baseline by design — a procurement officer
can see exactly why a score landed where it did, which matters more for a
compliance tool than a black-box model would.

## Notes on scope

This is a hackathon-stage MVP. Things intentionally kept simple that a
production rollout would harden further: single officer role (no
multi-department RBAC yet), keyword-based matching rather than a trained
classifier, and no e-signature/digital-signature verification of documents.
The architecture (a clean matching/scoring layer decoupled from
extraction) is built so any of those can be swapped in without touching the
rest of the app.
