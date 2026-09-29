# AI Bid Compliance Checker — Byte Busters (SIH 2026)

[![CI](https://github.com/Hare-Prasath-A-P-01/Bid-Compilance/actions/workflows/ci.yml/badge.svg)](https://github.com/Hare-Prasath-A-P-01/Bid-Compilance/actions/workflows/ci.yml)
[![Render Deployment](https://img.shields.io/badge/Render-Deployed%20Live-brightgreen)](https://bytebusters-bidcompliance.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise AI-powered procurement compliance verification system that checks tender bid documents against statutory procurement checklists automatically. It extracts text from PDFs and scans via OCR, matches documents to requirements, detects expired or corrupted submissions, calculates defensible compliance scores, and generates official PDF evaluation certificates.

Built for **Smart India Hackathon 2026** (Problem Statement: **SIH26100**) by **Byte Busters**.

---

## 🌐 Live Cloud Deployment

| Service | Link | Description |
|---|---|---|
| **Web Application (UI)** | [https://bid-compliance-frontend.onrender.com](https://bid-compliance-frontend.onrender.com) | Live React dashboard for procurement officers and reviewers |
| **Backend REST API** | [https://bid-compliance-api.onrender.com](https://bid-compliance-api.onrender.com) | FastAPI backend service with OCR & compliance engine |
| **Interactive API Docs** | [https://bid-compliance-api.onrender.com/docs](https://bid-compliance-api.onrender.com/docs) | Swagger UI for exploring and testing API endpoints |

### Demo Credentials
- **Email:** `officer@sih.gov.in`
- **Password:** `ByteBusters@2026`
- **Pre-seeded Tender:** `SIH26100-DEMO` (Supply of IT Equipment — 8 Statutory Requirements)

---

## 🚀 Key Features

- **Tender Lifecycle & Checklist Setup**: Procurement officers define mandatory/critical document checklists (GST, PAN, EMD proof, Technical/Financial bids) with custom matching keywords and weights.
- **Multimodal Document Processing**: Extracts text from native PDFs via `pdfplumber` and optical scans/images via `pytesseract` (Tesseract OCR).
- **Automated Compliance Engine**: Rule-based matching engine pairs uploaded documents to requirements, checks validity dates, flags expired/blank files, and computes a 0–100 compliance score with Low/Medium/High risk ratings.
- **Official PDF Evaluation Certificates**: Generates tamper-evident, downloadable PDF compliance certificates with QR-ready audit summaries via ReportLab.
- **Role-Based Access Control (RBAC)**: Enforces department-scoped permissions across Admin, Procurement Officer, and Reviewer roles with designated review queues.
- **Enterprise Security Hardening**: Magic-byte MIME type validation, SHA-256 duplicate document prevention, enterprise password complexity, secure session handling, and HTTP security headers (CSP, HSTS).
- **Complete Audit Trail**: Immutable logging of every upload, status transition, review action, and decision for full regulatory transparency.
- **Optional LLM Explanations**: Integrates with Claude (`claude-sonnet-4-6`) to provide plain-English summaries of flagged non-compliance issues.

---

## 🛠️ Architecture & Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite, React Router, Vanilla CSS Design System |
| **Backend** | FastAPI (Python 3.11), SQLAlchemy 2.0 ORM, Alembic migrations |
| **Database** | PostgreSQL (Production on Render) / SQLite (Local dev) |
| **Document Processing** | `pdfplumber`, `pytesseract` (Tesseract OCR Engine), Pillow |
| **Report Generation** | ReportLab (Vector PDF Generation) |
| **Security & Auth** | JWT (`python-jose`), bcrypt password hashing, magic-byte inspection |
| **Infrastructure** | Docker, Docker Compose, Nginx, Render Cloud Blueprints |
| **CI / CD** | GitHub Actions (Unit, Integration & E2E workflow tests) |

---

## 🧪 Testing the Live App with Sample Documents

The repository includes ready-to-upload test documents in [`sample_documents/`](./sample_documents/):

1. Log into the live web app with `officer@sih.gov.in` / `ByteBusters@2026`.
2. Open the demo tender: **SIH26100-DEMO**.
3. Create a new bid (e.g., bidder: *Apex Technologies*).
4. Upload files from `sample_documents/`:
   - `GST_Certificate.txt` ➔ Automatically matches **GST Registration Certificate** (Pass).
   - `PAN_Card.txt` ➔ Automatically matches **PAN Card** (Pass).
   - `EMD_Proof_Valid.txt` ➔ Automatically matches **EMD Proof** (Pass).
   - `Expired_EMD_Receipt.txt` ➔ Triggers **Date Expiry** flag (Mismatched / Review required).
   - `FLAG_Blank_Scan.txt` ➔ Triggers **Blank / Corrupted Scan** flag.
5. Click **"Download PDF Certificate"** to export the official evaluation report.

---

## 💻 Local Development Setup

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Hare-Prasath-A-P-01/Bid-Compilance.git
cd Bid-Compilance

# Start PostgreSQL, Backend API, and Frontend
docker compose up --build
```
- Open **http://localhost:4173** in your browser.
- Demo login: `officer@sih.gov.in` / `ByteBusters@2026`

---

### Option 2: Manual Setup (Without Docker)

#### 1. Backend:
```bash
cd backend
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend:
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** (Vite automatically proxies `/api` to port 8000).

---

## 📁 Repository Structure

```text
├── backend/
│   ├── alembic/              # Database migration versions & configuration
│   ├── app/
│   │   ├── routers/          # API endpoints (auth, tenders, bids, documents, compliance, reviews)
│   │   ├── services/         # Compliance engine, document processor, PDF generator, LLM
│   │   ├── models.py         # SQLAlchemy ORM models with composite indexing
│   │   ├── schemas.py        # Pydantic validation schemas & security validators
│   │   ├── auth.py           # JWT token generation & password hashing
│   │   ├── database.py       # DB engine, connection pooling & session management
│   │   └── main.py           # FastAPI application entrypoint & middleware
│   ├── tests/                # Automated test suite (18/18 passing)
│   ├── Dockerfile            # Container definition with Python 3.11 & Tesseract OCR
│   ├── requirements.txt      # Python dependencies
│   └── seed.py               # Database initial setup & demo seeding
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, TenderDetail, BidDetail, ReviewQueue, AdminUsers
│   │   ├── components/       # Layout Shell, RiskBadge, navigation
│   │   └── api/client.js     # Axios client with automatic routing & token interceptors
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite bundler configuration
├── sample_documents/         # Test documents for valid and flagged bid compliance scenarios
├── .github/workflows/ci.yml  # GitHub Actions CI pipeline
├── render.yaml               # 1-click cloud deployment blueprint for Render
└── docker-compose.yml        # Multi-container orchestration configuration
```

---

## 🔒 Security & Compliance Standards

- **Zero-Storage Secrets**: All sensitive keys (`SECRET_KEY`, DB passwords) are injected via environment variables.
- **Defense in Depth**: Uploaded files undergo header analysis, size bounds (10MB max), and content hashing.
- **Audit Defensibility**: Complete traceability with user IDs, timestamps, and action hashes for tender governance.

---

## 👥 Authors & Acknowledgments

- **Lead Developer & Maintainer:** [Hare Prasath A P](https://github.com/Hare-Prasath-A-P-01)
- **Team:** Byte Busters
- **Event:** Smart India Hackathon (SIH 2026) — Problem Statement ID: **SIH26100**
