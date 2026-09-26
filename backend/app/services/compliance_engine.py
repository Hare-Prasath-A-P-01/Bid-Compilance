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
