import unittest
import io

from app import models
from app.services.pdf_report import generate_compliance_pdf


class PdfReportTests(unittest.TestCase):
    def test_generate_compliance_pdf_produces_valid_pdf_stream(self):
        tender = models.Tender(
            id=1,
            reference_no="SIH26100-TEST",
            title="Supply of High Performance Compute Nodes",
            department="Ministry of Electronics & IT",
        )
        req1 = models.Requirement(id=1, name="GST Registration", keywords="gst", mandatory=True)
        req2 = models.Requirement(id=2, name="PAN Card", keywords="pan", mandatory=True)

        doc1 = models.BidDocument(
            id=101,
            original_filename="GST_Certificate.pdf",
            status=models.DocumentStatus.matched,
            requirement=req1,
            matched_keywords="gst, gstin",
            extraction_method="pdfplumber",
            text_quality=0.95,
            review_status="approved",
            review_comment="Valid verified GSTIN certificate.",
        )
        doc2 = models.BidDocument(
            id=102,
            original_filename="PAN_Card.pdf",
            status=models.DocumentStatus.matched,
            requirement=req2,
            matched_keywords="pan",
            extraction_method="pdfplumber",
            text_quality=0.92,
            review_status="pending",
            notes="Document matched",
        )

        bid = models.Bid(
            id=1,
            tender_id=1,
            bidder_name="Acme Tech Innovations",
            bidder_company="Acme Corp Global",
            submission_status="Under review",
            submitted_version=1,
            compliance_score=94.5,
            risk_level=models.RiskLevel.low,
            documents=[doc1, doc2],
        )

        pdf_stream = generate_compliance_pdf(bid, tender)

        self.assertIsInstance(pdf_stream, io.BytesIO)
        content = pdf_stream.getvalue()
        self.assertTrue(len(content) > 1000)
        self.assertTrue(content.startswith(b"%PDF-"))

    def test_generate_compliance_pdf_high_risk_badge(self):
        tender = models.Tender(
            id=2,
            reference_no="REF-HIGH-RISK",
            title="Security Surveillance Deployment",
            department="Department of Defence",
        )
        bid = models.Bid(
            id=2,
            tender_id=2,
            bidder_name="Flagged Bidder Ltd",
            submission_status="Draft",
            submitted_version=0,
            compliance_score=35.0,
            risk_level=models.RiskLevel.high,
            documents=[],
        )

        pdf_stream = generate_compliance_pdf(bid, tender)
        content = pdf_stream.getvalue()
        self.assertTrue(len(content) > 1000)
        self.assertTrue(content.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
