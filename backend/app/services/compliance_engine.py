"""
Core compliance logic.

This module intentionally keeps the rule-based engine explainable while making
it more realistic for the procurement workflow: a single uploaded file can
match multiple requirements, and the evaluation should reflect missing,
matched, and mismatched requirements in a more nuanced way.
"""
import datetime
import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

from app import models

MATCH_THRESHOLD = 0.34

DATE_PATTERN = re.compile(
    r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})|(\d{4})[/-](\d{1,2})[/-](\d{1,2})"
)
MONTH_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
    re.IGNORECASE,
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip().lower()


def _score_keywords(text: str, keywords: List[str]) -> float:
    if not keywords:
        return 0.0
    text_l = _normalize_text(text)
    hits = sum(1 for kw in keywords if kw.strip() and _term_in_text(kw, text_l))
    return hits / len(keywords)


def _keyword_list(requirement: "models.Requirement") -> List[str]:
    return [k.strip() for k in requirement.keywords.split(",") if k.strip()]


def _alias_list(requirement: "models.Requirement") -> List[str]:
    return [a.strip() for a in (requirement.aliases or "").split(",") if a.strip()]


def _matching_terms(requirement: "models.Requirement") -> List[str]:
    return _keyword_list(requirement) + _alias_list(requirement)


def _term_in_text(term: str, text: str) -> bool:
    term_l = _normalize_text(term)
    if term_l in text:
        return True
    tokens = re.findall(r"[a-z0-9]+", text)
    term_tokens = term_l.split()
    windows = [" ".join(tokens[i:i + len(term_tokens)]) for i in range(len(tokens) - len(term_tokens) + 1)]
    return any(difflib.SequenceMatcher(None, term_l, window).ratio() >= 0.86 for window in windows)


def matching_keywords(text: str, requirement: "models.Requirement") -> List[str]:
    """Return exact or near-matching requirement terms found in document text."""
    text_l = _normalize_text(text)
    return [term for term in _matching_terms(requirement) if _term_in_text(term, text_l)]


def find_best_matches(text: str, requirements: List["models.Requirement"]) -> List[Dict[str, Any]]:
    """Return all requirements that meaningfully match the document, ranked by confidence."""
    if not text or not text.strip():
        return []

    ranked = []
    for req in requirements:
        keywords = _matching_terms(req)
        score = _score_keywords(text, keywords)
        if score >= MATCH_THRESHOLD:
            ranked.append({
                "requirement": req,
                "name": req.name,
                "score": round(score, 2),
                "evidence": matching_keywords(text, req),
            })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def classify_document(text: str, requirements: List["models.Requirement"]) -> Tuple[Optional["models.Requirement"], float]:
    """Return the strongest single requirement match for a document, plus confidence 0-1."""
    matches = find_best_matches(text, requirements)
    if not matches:
        best_score = max((_score_keywords(text, _matching_terms(req)) for req in requirements), default=0.0)
        return None, round(best_score, 2)

    best = matches[0]
    return best["requirement"], round(best["score"], 2)


def _parse_date(raw: str) -> Optional[datetime.datetime]:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def extract_expiry_date(text: str) -> Optional[datetime.datetime]:
    """Extract a date near an expiry/validity label for consistent UI and scoring."""
    label_pattern = re.compile(r"(?:expiry|expiration|expires|valid until|valid through|validity)\s*[:\-]?", re.IGNORECASE)
    for label in label_pattern.finditer(text or ""):
        window = text[label.end():label.end() + 90]
        candidates = [match.group(0) for match in DATE_PATTERN.finditer(window)]
        candidates += [match.group(0) for match in MONTH_DATE_PATTERN.finditer(window)]
        for candidate in candidates:
            parsed = _parse_date(candidate)
            if parsed:
                return parsed
    return None


def detect_issues(text: str, text_quality: Optional[float] = None) -> List[str]:
    """Heuristics for expired, blank, or weakly extracted documents."""
    issues: List[str] = []
    if not text:
        return issues

    text_l = _normalize_text(text)
    if not text_l:
        return ["Document is blank or has no readable text."]

    if len(text.strip()) < 40 or (text_quality is not None and text_quality < 0.35):
        issues.append("Extracted text is very short — document may be blank, corrupted, or unreadable")

    expiry_date = extract_expiry_date(text)
    if expiry_date and expiry_date.date() <= datetime.datetime.now().date():
        issues.append(f"Document expiry date has passed ({expiry_date.strftime('%d-%m-%Y')})")

    if "expired" in text_l:
        issues.append("Document text explicitly mentions 'expired'")

    if "not valid" in text_l or "invalid" in text_l:
        issues.append("Document contains an invalid or non-current validity statement")

    suspicious_terms = ("forged", "tampered", "altered", "fake document", "counterfeit")
    found_suspicious = [term for term in suspicious_terms if term in text_l]
    if found_suspicious:
        issues.append(f"Suspicious document wording detected: {', '.join(found_suspicious)}")

    return issues


def evaluate_bid(bid: "models.Bid", requirements: List["models.Requirement"]) -> Tuple[float, str]:
    """Compute overall compliance score and risk using matched, mismatched, and missing requirements."""
    if not requirements:
        return 0.0, models.RiskLevel.high.value

    mandatory_reqs = [r for r in requirements if r.mandatory]
    evaluated_reqs = mandatory_reqs if mandatory_reqs else requirements
    total_weight = sum(max(float(getattr(req, "weight", 1.0) or 1.0), 0.1) for req in evaluated_reqs)
    required_ids = {r.id for r in mandatory_reqs} if mandatory_reqs else {r.id for r in requirements}

    matched_ids = {
        d.requirement_id for d in bid.documents
        if d.status == models.DocumentStatus.matched and d.requirement_id is not None and d.requirement_id in required_ids
    }
    mismatched_ids = {
        d.requirement_id for d in bid.documents
        if d.status == models.DocumentStatus.mismatched and d.requirement_id is not None and d.requirement_id in required_ids
    }

    matched_weight = sum(
        max(float(getattr(req, "weight", 1.0) or 1.0), 0.1)
        for req in evaluated_reqs if req.id in matched_ids
    )
    mismatched_weight = sum(
        max(float(getattr(req, "weight", 1.0) or 1.0), 0.1)
        for req in evaluated_reqs if req.id in mismatched_ids
    )
    missing_reqs = [req for req in evaluated_reqs if req.id not in matched_ids and req.id not in mismatched_ids]
    missing_count = len(missing_reqs)
    critical_missing = sum(1 for req in missing_reqs if getattr(req, "critical", False))

    score = (matched_weight / total_weight) * 100 if total_weight else 0.0
    score -= (mismatched_weight / total_weight) * 20 if total_weight else 0.0
    score -= critical_missing * 15
    score = max(0.0, min(100.0, round(score, 1)))

    if score >= 85 and not mismatched_ids and missing_count == 0:
        risk = models.RiskLevel.low.value
    elif score >= 60 and critical_missing == 0 and missing_count <= 1:
        risk = models.RiskLevel.medium.value
    else:
        risk = models.RiskLevel.high.value

    return score, risk


def classify_document_type(text: str, filename: Optional[str] = None, req_name: Optional[str] = None) -> str:
    combined = f"{filename or ''} {req_name or ''} {(text or '')[:1000]}".lower()
    if "gst" in combined or "goods and services tax" in combined or "gstin" in combined:
        return "GST Registration Certificate"
    if "pan" in combined or "permanent account number" in combined:
        return "PAN Card"
    if "emd" in combined or "earnest money deposit" in combined or "bank guarantee" in combined:
        return "Earnest Money Deposit (EMD) Proof"
    if "incorporation" in combined or "company registration" in combined or "cin" in combined or "registrar of companies" in combined:
        return "Company Registration Certificate"
    if "experience" in combined or "completion certificate" in combined:
        return "Experience Certificate"
    if "technical bid" in combined or "technical proposal" in combined or "specification" in combined:
        return "Technical Bid Document"
    if "financial bid" in combined or "price bid" in combined or "boq" in combined or "quotation" in combined:
        return "Financial Bid Document"
    if "authorized signatory" in combined or "power of attorney" in combined or "authorization" in combined:
        return "Authorized Signatory Letter"
    if req_name:
        return req_name
    return "General Bid Document"


def extract_structured_fields(text: str, filename: Optional[str] = None, req_name: Optional[str] = None) -> Dict[str, str]:
    """Extract key business and statutory fields from document text."""
    fields: Dict[str, str] = {}
    if not text or not text.strip():
        return fields

    doc_type = classify_document_type(text, filename, req_name)

    # 1. GST Identification
    gst_match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b", text)
    if gst_match:
        fields["GSTIN"] = gst_match.group(0)

    # 2. PAN Identification
    pan_match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", text)
    if pan_match:
        fields["PAN"] = pan_match.group(0)

    # 3. CIN (Corporate Identity Number)
    cin_match = re.search(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b", text)
    if cin_match:
        fields["CIN"] = cin_match.group(0)

    # 4. Dates
    expiry = extract_expiry_date(text)
    if expiry:
        fields["Validity / Expiry Date"] = expiry.strftime("%d/%m/%Y")

    date_matches = [m.group(0) for m in DATE_PATTERN.finditer(text)]
    if date_matches and "Validity / Expiry Date" not in fields:
        fields["Detected Date"] = date_matches[0]

    # 5. Entity / Company / Applicant Name
    legal_name_match = re.search(r"(?:Legal Name|Name of Taxpayer|Applicant|Name|Company Name)\s*[:\-]?\s*([^\n\r]+)", text, re.IGNORECASE)
    if legal_name_match:
        name_val = legal_name_match.group(1).strip()
        if len(name_val) > 2 and len(name_val) < 80:
            fields["Entity Name"] = name_val

    # 6. Trade Name
    trade_name_match = re.search(r"(?:Trade Name)\s*[:\-]?\s*([^\n\r]+)", text, re.IGNORECASE)
    if trade_name_match:
        trade_val = trade_name_match.group(1).strip()
        if len(trade_val) > 2 and len(trade_val) < 80:
            fields["Trade Name"] = trade_val

    # 7. Amounts / Deposits
    amt_match = re.search(r"(?:Deposit Amount|Amount|INR|Rs\.?)\s*[:\-]?\s*(?:INR\s*|Rs\.?\s*)?([0-9,]+(?:\.[0-9]{2})?)", text, re.IGNORECASE)
    if amt_match:
        fields["Amount / Valuation"] = f"INR {amt_match.group(1).strip()}"

    # 8. Reference Numbers
    ref_match = re.search(r"(?:Reference No|Ref No|FDR No|EMD Reference No|Guarantee No)\s*[:\-]?\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
    if ref_match:
        fields["Reference Number"] = ref_match.group(1).strip()

    tender_ref_match = re.search(r"(?:Tender Reference|Tender Ref)\s*[:\-]?\s*([A-Za-z0-9\-_/]+)", text, re.IGNORECASE)
    if tender_ref_match:
        fields["Tender Reference"] = tender_ref_match.group(1).strip()

    # 9. Issuing Authority / Bank
    for bank in [
        "State Bank of India", "Punjab National Bank", "HDFC Bank", "ICICI Bank",
        "Bank of Baroda", "Canara Bank", "Government of India",
        "Income Tax Department", "Ministry of Electronics & IT"
    ]:
        if bank.lower() in text.lower():
            fields["Issuing Authority"] = bank
            break

    # 10. Statutory Verification Status
    if "GST" in doc_type:
        fields["Statutory Portal Check"] = "API integration ready (Simulated verification in Demo mode)"
    elif "PAN" in doc_type:
        fields["Statutory Portal Check"] = "API integration ready (NSDL / ITD Simulated verification in Demo mode)"
    elif "EMD" in doc_type:
        fields["Statutory Portal Check"] = "API integration ready (Core Banking SFMS Gateway Simulated in Demo mode)"
    elif "Company" in doc_type:
        fields["Statutory Portal Check"] = "API integration ready (MCA21 V3 Portal Simulated in Demo mode)"
    else:
        fields["Statutory Portal Check"] = "API integration ready (Demo mode)"

    return fields


def summarize_extracted_value(doc: "models.BidDocument") -> str:
    """Summarize key extracted values into a concise human-readable one-liner."""
    if not doc or not doc.extracted_text:
        return "No extractable text"

    req_name = doc.requirement.name if doc.requirement else None
    fields = extract_structured_fields(doc.extracted_text, doc.original_filename, req_name)
    parts = []
    if "GSTIN" in fields:
        parts.append(f"GSTIN: {fields['GSTIN']}")
    if "PAN" in fields:
        parts.append(f"PAN: {fields['PAN']}")
    if "CIN" in fields:
        parts.append(f"CIN: {fields['CIN']}")
    if "Amount / Valuation" in fields:
        parts.append(f"Deposit: {fields['Amount / Valuation']}")
    if "Entity Name" in fields:
        parts.append(fields["Entity Name"])
    if "Validity / Expiry Date" in fields:
        parts.append(f"Valid to: {fields['Validity / Expiry Date']}")

    if parts:
        return " | ".join(parts[:3])

    if doc.matched_keywords:
        return f"Keywords: {doc.matched_keywords}"

    return f"File: {doc.original_filename} (Text: {len(doc.extracted_text)} chars)"


def build_verification_details(
    bid: "models.Bid",
    requirements: List["models.Requirement"]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Build the comprehensive, requirement-by-requirement verification checklist and stats."""
    checklist: List[Dict[str, Any]] = []

    doc_by_req: Dict[int, List["models.BidDocument"]] = {}
    for doc in bid.documents:
        if doc.requirement_id:
            doc_by_req.setdefault(doc.requirement_id, []).append(doc)

    for req in requirements:
        matching_docs = doc_by_req.get(req.id, [])
        doc = matching_docs[0] if matching_docs else None

        if not doc:
            status = "Missing"
            status_label = "✕ Missing"
            extracted_val = "Not Submitted"
            matched_doc_name = None
            evidence = "—"
            conf = 0.0
            if req.mandatory:
                reason = f"Mandatory requirement '{req.name}' has no matching document uploaded. Submission is incomplete."
            else:
                reason = f"Optional requirement '{req.name}' was not uploaded by bidder."
        else:
            matched_doc_name = doc.original_filename
            extracted_val = summarize_extracted_value(doc)
            evidence = doc.matched_keywords or (", ".join(matching_keywords(doc.extracted_text, req)) if doc.extracted_text else "—")
            conf = doc.match_confidence

            issues = detect_issues(doc.extracted_text, doc.text_quality)
            if doc.status == models.DocumentStatus.matched and not issues and doc.review_status != "rejected":
                status = "Compliant"
                status_label = "✓ Compliant"
                reason = f"Document '{doc.original_filename}' satisfies statutory requirement '{req.name}'. Content verified, valid active dates, no tampering detected."
            elif issues:
                status = "Mismatch"
                status_label = "✕ Mismatch"
                reason = f"Compliance flag on '{doc.original_filename}': {issues[0]}."
            elif doc.review_status == "rejected":
                status = "Mismatch"
                status_label = "✕ Mismatch"
                reason = f"Reviewer rejected '{doc.original_filename}': {doc.review_comment or 'Non-compliant document'}."
            elif doc.status == models.DocumentStatus.mismatched:
                status = "Mismatch"
                status_label = "✕ Mismatch"
                reason = doc.notes or f"Document did not satisfy statutory criteria for '{req.name}'."
            else:
                status = "Needs Review"
                status_label = "⚠ Needs Review"
                reason = doc.notes or "Document match confidence requires officer manual confirmation."

        checklist.append({
            "requirement_id": req.id,
            "requirement_name": req.name,
            "mandatory": bool(req.mandatory),
            "critical": bool(getattr(req, "critical", False)),
            "weight": float(getattr(req, "weight", 1.0) or 1.0),
            "status": status,
            "status_label": status_label,
            "extracted_value": extracted_val,
            "matched_document": matched_doc_name,
            "evidence": evidence,
            "reason": reason,
            "confidence": conf,
            "portal_verification": "API integration ready (Demo mode)",
        })

    total_checks = len(requirements)
    passed_count = sum(1 for item in checklist if item["status"] == "Compliant")
    missing_count = sum(1 for item in checklist if item["status"] == "Missing")
    mismatched_count = sum(1 for item in checklist if item["status"] in ("Mismatch", "Needs Review"))

    summary_stats = {
        "total_checks": total_checks,
        "passed": passed_count,
        "missing": missing_count,
        "mismatched_needs_review": mismatched_count,
        "compliance_score": bid.compliance_score if bid.compliance_score is not None else 0.0,
        "risk_level": bid.risk_level.value if hasattr(bid.risk_level, "value") else str(bid.risk_level or "High"),
    }

    return checklist, summary_stats

