"""
Optional LLM assist layer.

The rule-based compliance_engine works standalone (no API key needed) and is
what actually decides Matched/Mismatched/Missing. When ANTHROPIC_API_KEY is
set, this module is used on top of it purely to produce a short, readable
explanation of *why* a document was flagged -- e.g. "Matched but the
certificate's validity date appears to have lapsed" -- which is what the
"LLM + NLP - Requirement Analysis" line in the tech stack refers to.

If no key is configured, callers fall back to a templated explanation, so the
API stays fully optional for local development and grading.
"""
import json
import re

import httpx

from app.config import settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

SUGGESTION_LIBRARY = [
    ("GST Registration Certificate", "gst, goods and services tax, gstin", "tax registration"),
    ("PAN Card", "pan, permanent account number", "tax identity"),
    ("Company Registration Certificate", "certificate of incorporation, cin, registrar of companies", "company incorporation"),
    ("Technical Bid Document", "technical bid, technical proposal, specifications", "technical offer"),
    ("Financial Bid Document", "financial bid, price bid, quotation, boq", "commercial offer"),
    ("Experience Certificate", "experience certificate, prior work, completion certificate", "past performance"),
    ("EMD Proof", "emd, earnest money deposit, bid security", "tender security"),
    ("Authorized Signatory Letter", "authorized signatory, power of attorney, authorization letter", "signing authority"),
]


def _fallback_suggestions(text: str) -> list[dict]:
    text_l = (text or "").lower()
    suggestions = []
    for name, keywords, aliases in SUGGESTION_LIBRARY:
        if any(term in text_l for term in (*keywords.split(", "), *aliases.split(", "))):
            suggestions.append({"name": name, "keywords": keywords, "aliases": aliases, "mandatory": True, "critical": False, "weight": 1.0})
    return suggestions


def suggest_requirements(text: str) -> list[dict]:
    """Suggest checklist items; AI output is advisory and always validated/fallback-safe."""
    fallback = _fallback_suggestions(text)
    if not settings.ANTHROPIC_API_KEY:
        return fallback
    prompt = (
        "Extract procurement document requirements from the tender brief below. "
        "Return only a JSON array with objects containing name, keywords, aliases, "
        "mandatory, critical, and weight. Do not invent requirements not supported by the brief.\n\n"
        f"Tender brief:\n{text[:6000]}"
    )
    try:
        response = httpx.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": MODEL, "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]},
            timeout=20.0,
        )
        response.raise_for_status()
        content = "".join(part.get("text", "") for part in response.json().get("content", []) if part.get("type") == "text")
        match = re.search(r"\[.*\]", content, re.DOTALL)
        suggestions = json.loads(match.group(0)) if match else []
        valid = []
        for item in suggestions:
            if isinstance(item, dict) and item.get("name") and item.get("keywords"):
                valid.append({
                    "name": str(item["name"]),
                    "keywords": str(item["keywords"]),
                    "aliases": str(item.get("aliases", "")),
                    "mandatory": bool(item.get("mandatory", True)),
                    "critical": bool(item.get("critical", False)),
                    "weight": min(max(float(item.get("weight", 1.0)), 0.1), 10.0),
                })
        return valid or fallback
    except Exception:
        return fallback


def explain_match(requirement_name: str, extracted_text: str, issues: list[str]) -> str:
    if not settings.ANTHROPIC_API_KEY:
        if issues:
            return "Automated check flagged: " + "; ".join(issues)
        return f"Document text matched the expected content for '{requirement_name}'."

    prompt = (
        f"A tender compliance system matched an uploaded document to the requirement "
        f"'{requirement_name}'. Automated checks found these potential issues: "
        f"{issues if issues else 'none'}.\n\n"
        f"Document excerpt (first 800 chars):\n{extracted_text[:800]}\n\n"
        "In one short sentence, tell a procurement officer whether this document looks "
        "genuinely fine or needs manual review, and why. Be concise and factual."
    )
    try:
        resp = httpx.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return " ".join(parts).strip() or "LLM returned no explanation."
    except Exception as exc:  # noqa: BLE001
        return f"(LLM explanation unavailable: {exc})"
