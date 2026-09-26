import io
import unittest
import uuid
from fastapi.testclient import TestClient

from app.main import app


class E2EWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Login to obtain JWT bearer token
        login_res = self.client.post(
            "/api/auth/login",
            data={"username": "officer@sih.gov.in", "password": "ByteBusters@2026"},
        )
        self.assertEqual(login_res.status_code, 200, "Demo login failed")
        token_data = login_res.json()
        self.token = token_data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_unauthorized_access_rejected(self):
        res = self.client.get("/api/tenders")
        self.assertEqual(res.status_code, 401)

    def test_complete_procurement_lifecycle(self):
        # 1. Create a Tender
        tender_payload = {
            "reference_no": f"TENDER-E2E-{uuid.uuid4().hex[:8]}",
            "title": "E2E Automated Procurement Tender",

            "department": "Ministry of Electronics & IT",
            "theme": "National Security Computing",
            "description": "Enterprise end-to-end procurement test tender",
            "requirements": [
                {
                    "name": "GST Registration Certificate",
                    "keywords": "gst, goods and services tax, gstin",
                    "mandatory": True,
                    "critical": False,
                    "weight": 2.0,
                },
                {
                    "name": "PAN Card",
                    "keywords": "pan, permanent account number",
                    "mandatory": True,
                    "critical": False,
                    "weight": 1.0,
                },
            ],
        }
        res_tender = self.client.post("/api/tenders", json=tender_payload, headers=self.headers)
        self.assertEqual(res_tender.status_code, 200)
        tender = res_tender.json()
        tender_id = tender["id"]

        # 2. Register a Bid
        bid_payload = {
            "bidder_name": "Bharat Compute Tech Ltd",
            "bidder_company": "Bharat Tech Solutions",
        }
        res_bid = self.client.post(f"/api/tenders/{tender_id}/bids", json=bid_payload, headers=self.headers)
        self.assertEqual(res_bid.status_code, 200)
        bid = res_bid.json()
        bid_id = bid["id"]
        self.assertEqual(bid["submission_status"], "Draft")

        # 3. Upload a Document (GST Text Document)
        gst_doc_content = (
            "GOVERNMENT OF INDIA\n"
            "GOODS AND SERVICES TAX REGISTRATION CERTIFICATE\n"
            "GSTIN: 27ABCDE1234F1Z5\n"
            "Legal Name: Bharat Compute Tech Ltd\n"
            "Valid through: 31/12/2029\n"
        ).encode("utf-8")


        upload_files = {
            "file": ("GST_Registration.txt", io.BytesIO(gst_doc_content), "text/plain")
        }
        res_upload = self.client.post(
            f"/api/tenders/{tender_id}/bids/{bid_id}/documents",
            files=upload_files,
            headers=self.headers,
        )
        self.assertEqual(res_upload.status_code, 200)
        uploaded_doc = res_upload.json()
        self.assertEqual(uploaded_doc["status"], "Matched")
        self.assertIn("GST Registration Certificate", uploaded_doc["notes"])

        # 4. Fetch Compliance Evaluation
        res_compliance = self.client.get(
            f"/api/tenders/{tender_id}/bids/{bid_id}/compliance",
            headers=self.headers,
        )
        self.assertEqual(res_compliance.status_code, 200)
        compliance = res_compliance.json()
        self.assertIn("GST Registration Certificate", compliance["matched"])
        self.assertIn("PAN Card", compliance["missing"])

        # 5. Export CSV Report
        res_csv = self.client.get(f"/api/tenders/{tender_id}/bids/{bid_id}/export.csv", headers=self.headers)
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("text/csv", res_csv.headers["content-type"])
        self.assertIn("Bharat Compute Tech Ltd", res_csv.text)

        # 6. Export PDF Compliance Certificate
        res_pdf = self.client.get(f"/api/tenders/{tender_id}/bids/{bid_id}/export.pdf", headers=self.headers)
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.headers["content-type"], "application/pdf")
        self.assertTrue(res_pdf.content.startswith(b"%PDF-"))

        # 7. Check Audit Log
        res_audit = self.client.get(f"/api/tenders/{tender_id}/bids/{bid_id}/audit-log", headers=self.headers)
        self.assertEqual(res_audit.status_code, 200)
        actions = [log["action"] for log in res_audit.json()]
        self.assertIn("BID_CREATED", actions)
        self.assertIn("DOCUMENT_UPLOADED", actions)

        # 8. Submit Bid and verify document immutability
        res_submit = self.client.patch(
            f"/api/tenders/{tender_id}/bids/{bid_id}/status",
            json={"status": "Submitted"},
            headers=self.headers,
        )
        self.assertEqual(res_submit.status_code, 200)
        self.assertEqual(res_submit.json()["submission_status"], "Submitted")

        # Attempting to upload after submission must be rejected (409 Conflict)
        res_locked = self.client.post(
            f"/api/tenders/{tender_id}/bids/{bid_id}/documents",
            files=upload_files,
            headers=self.headers,
        )
        self.assertEqual(res_locked.status_code, 409)


if __name__ == "__main__":
    unittest.main()
