import unittest

from app import models
from app.services.compliance_engine import (
    detect_issues,
    evaluate_bid,
    extract_expiry_date,
    find_best_matches,
    matching_keywords,
)
from app.services.llm_service import suggest_requirements


class ComplianceEngineTests(unittest.TestCase):
    def test_find_best_matches_detects_multiple_relevant_requirements(self):
        requirements = [
            models.Requirement(id=1, name="GST Registration Certificate", keywords="gst, goods and services tax, gstin", mandatory=True),
            models.Requirement(id=2, name="PAN Card", keywords="pan, permanent account number", mandatory=True),
            models.Requirement(id=3, name="Technical Bid Document", keywords="technical bid, technical proposal, specifications", mandatory=True),
        ]

        text = (
            "GSTIN 27ABCDE1234F1Z5. PAN AAAPL1234C. Technical bid for the supply of IT equipment with "
            "technical proposal and specifications details."
        )

        matches = find_best_matches(text, requirements)
        names = [item["name"] for item in matches]

        self.assertIn("GST Registration Certificate", names)
        self.assertIn("PAN Card", names)
        self.assertIn("Technical Bid Document", names)
        self.assertEqual(matches[0]["name"], "Technical Bid Document")

    def test_matching_keywords_returns_evidence_for_explanation(self):
        requirement = models.Requirement(
            id=1,
            name="GST Certificate",
            keywords="gst, gstin, registration",
        )

        evidence = matching_keywords("GSTIN 27ABCDE1234F1Z5 registration details", requirement)

        self.assertEqual(evidence, ["gst", "gstin", "registration"])

    def test_matching_keywords_supports_aliases_and_fuzzy_wording(self):
        requirement = models.Requirement(
            id=1,
            name="Technical Bid",
            keywords="technical proposal",
            aliases="technical offer",
        )

        evidence = matching_keywords("This technical ofer contains the requested specifications", requirement)

        self.assertEqual(evidence, ["technical offer"])

    def test_detect_issues_flags_suspicious_document_language(self):
        issues = detect_issues("This document appears altered and may be a forged certificate.")

        self.assertTrue(any("suspicious" in issue.lower() for issue in issues))

    def test_requirement_suggestions_have_safe_local_fallback(self):
        suggestions = suggest_requirements("Submit GST registration, PAN card, technical bid and financial quotation.")
        names = {item["name"] for item in suggestions}

        self.assertIn("GST Registration Certificate", names)
        self.assertIn("PAN Card", names)
        self.assertIn("Technical Bid Document", names)

    def test_detect_issues_flags_expired_and_blank_documents(self):
        expired_text = "GST registration certificate expired on 12-03-2022 and not valid after expiry date."
        blank_text = "   "

        self.assertTrue(any("expired" in issue.lower() for issue in detect_issues(expired_text)))
        self.assertTrue(any("blank" in issue.lower() or "short" in issue.lower() for issue in detect_issues(blank_text)))

    def test_extract_expiry_date_supports_labeled_numeric_and_month_dates(self):
        numeric = extract_expiry_date("Certificate expiry: 12-03-2022")
        month_name = extract_expiry_date("Valid through: 12 March 2027")

        self.assertEqual(numeric.strftime("%Y-%m-%d"), "2022-03-12")
        self.assertEqual(month_name.strftime("%Y-%m-%d"), "2027-03-12")

    def test_evaluate_bid_scores_missing_and_mismatched_documents(self):
        requirements = [
            models.Requirement(id=1, name="GST Registration Certificate", keywords="gst", mandatory=True),
            models.Requirement(id=2, name="PAN Card", keywords="pan", mandatory=True),
            models.Requirement(id=3, name="Technical Bid Document", keywords="technical bid", mandatory=True),
        ]

        bid = models.Bid(
            id=1,
            tender_id=1,
            bidder_name="Test Bidder",
            documents=[
                models.BidDocument(id=1, requirement_id=1, status=models.DocumentStatus.matched),
                models.BidDocument(id=2, requirement_id=3, status=models.DocumentStatus.mismatched),
            ],
        )

        score, risk = evaluate_bid(bid, requirements)

        self.assertLess(score, 100)
        self.assertEqual(risk, models.RiskLevel.high.value)

    def test_evaluate_bid_weights_critical_requirements(self):
        requirements = [
            models.Requirement(id=1, name="Financial Bid", keywords="financial", mandatory=True, critical=True, weight=3),
            models.Requirement(id=2, name="PAN Card", keywords="pan", mandatory=True, critical=False, weight=1),
        ]
        bid = models.Bid(
            id=2,
            tender_id=1,
            bidder_name="Weighted Bidder",
            documents=[models.BidDocument(requirement_id=1, status=models.DocumentStatus.matched)],
        )

        score, risk = evaluate_bid(bid, requirements)

        self.assertEqual(score, 75.0)
        self.assertEqual(risk, models.RiskLevel.medium.value)

        requirements[1].critical = True
        score, risk = evaluate_bid(bid, requirements)

        self.assertEqual(score, 60.0)
        self.assertEqual(risk, models.RiskLevel.high.value)

    def test_extract_structured_fields_and_classification(self):
        from app.services.compliance_engine import classify_document_type, extract_structured_fields

        gst_text = (
            "GOVERNMENT OF INDIA\n"
            "GOODS AND SERVICES TAX REGISTRATION CERTIFICATE\n"
            "Registration Number (GSTIN): 27ABCDE1234F1Z5\n"
            "Legal Name: Acme Tech Solutions Pvt Ltd\n"
            "Trade Name: Acme Technologies\n"
            "Period of Validity: From 01/04/2022 to 31/12/2029\n"
        )
        doc_type = classify_document_type(gst_text, "GST_Certificate.txt", "GST Registration Certificate")
        self.assertEqual(doc_type, "GST Registration Certificate")

        fields = extract_structured_fields(gst_text, "GST_Certificate.txt", doc_type)
        self.assertEqual(fields.get("GSTIN"), "27ABCDE1234F1Z5")
        self.assertEqual(fields.get("Entity Name"), "Acme Tech Solutions Pvt Ltd")
        self.assertIn("API integration ready", fields.get("Statutory Portal Check", ""))

    def test_build_verification_details_checklist_and_stats(self):
        from app.services.compliance_engine import build_verification_details

        requirements = [
            models.Requirement(id=1, name="GST Registration Certificate", keywords="gst", mandatory=True),
            models.Requirement(id=2, name="PAN Card", keywords="pan", mandatory=True),
        ]
        bid = models.Bid(
            id=10,
            tender_id=1,
            bidder_name="SIH Bidder",
            compliance_score=90.0,
            risk_level=models.RiskLevel.low,
            documents=[
                models.BidDocument(
                    id=1,
                    requirement_id=1,
                    original_filename="GST_Doc.txt",
                    extracted_text="GSTIN 27ABCDE1234F1Z5 Legal Name: Acme Tech",
                    status=models.DocumentStatus.matched,
                    match_confidence=0.95,
                    matched_keywords="gst, gstin",
                )
            ],
        )
        checklist, stats = build_verification_details(bid, requirements)

        self.assertEqual(stats["total_checks"], 2)
        self.assertEqual(stats["passed"], 1)
        self.assertEqual(stats["missing"], 1)
        self.assertEqual(checklist[0]["status"], "Compliant")
        self.assertEqual(checklist[0]["status_label"], "✓ Compliant")
        self.assertEqual(checklist[1]["status"], "Missing")
        self.assertEqual(checklist[1]["status_label"], "✕ Missing")


if __name__ == "__main__":
    unittest.main()

