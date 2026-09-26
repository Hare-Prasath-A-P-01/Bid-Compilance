import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import validate_password_strength
from app.routers.documents import validate_magic_bytes


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_strong_password_validation(self):
        # Valid strong password
        self.assertEqual(validate_password_strength("ByteBusters@2026"), "ByteBusters@2026")
        self.assertEqual(validate_password_strength("GovProcure#987!Secure"), "GovProcure#987!Secure")

        # Too short (< 10)
        with self.assertRaises(ValueError) as ctx:
            validate_password_strength("Short1@a")
        self.assertIn("at least 10 characters", str(ctx.exception))

        # No uppercase
        with self.assertRaises(ValueError) as ctx:
            validate_password_strength("alllowercase123!")
        self.assertIn("uppercase letter", str(ctx.exception))

        # No lowercase
        with self.assertRaises(ValueError) as ctx:
            validate_password_strength("ALLLOWERCASE123!")
        self.assertIn("lowercase letter", str(ctx.exception))

        # No number
        with self.assertRaises(ValueError) as ctx:
            validate_password_strength("NoNumbersHere!@#")
        self.assertIn("number", str(ctx.exception))

        # No special character
        with self.assertRaises(ValueError) as ctx:
            validate_password_strength("NoSpecialChar12345")
        self.assertIn("special character", str(ctx.exception))

    def test_magic_byte_inspection_pdf(self):
        valid_pdf = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj"
        ok, msg = validate_magic_bytes(valid_pdf, ".pdf")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

        fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00... disguised windows executable"
        ok, msg = validate_magic_bytes(fake_pdf, ".pdf")
        self.assertFalse(ok)
        self.assertIn("Invalid PDF", msg)

    def test_magic_byte_inspection_images(self):
        valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        ok, msg = validate_magic_bytes(valid_png, ".png")
        self.assertTrue(ok)

        fake_png = b"Not a real png"
        ok, msg = validate_magic_bytes(fake_png, ".png")
        self.assertFalse(ok)
        self.assertIn("Invalid PNG", msg)

        valid_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        ok, msg = validate_magic_bytes(valid_jpg, ".jpg")
        self.assertTrue(ok)

        fake_jpg = b"random content"
        ok, msg = validate_magic_bytes(fake_jpg, ".jpg")
        self.assertFalse(ok)
        self.assertIn("Invalid JPEG", msg)

    def test_magic_byte_inspection_text(self):
        valid_txt = "Standard ASCII or UTF-8 text document with tender content.".encode("utf-8")
        ok, msg = validate_magic_bytes(valid_txt, ".txt")
        self.assertTrue(ok)

        disguised_binary = b"ELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        ok, msg = validate_magic_bytes(disguised_binary, ".txt")
        self.assertFalse(ok)
        self.assertIn("binary null bytes", msg)

    def test_security_headers_present_on_api_responses(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        # Verify enterprise security headers
        headers = response.headers
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy", ""))
        self.assertIn("camera=()", headers.get("Permissions-Policy", ""))
        self.assertTrue(bool(headers.get("X-Request-ID")))


if __name__ == "__main__":
    unittest.main()
