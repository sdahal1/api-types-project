"""Offline behavior tests. These do not emulate API Gateway or enforce keys."""

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from app import handler


class ProductLookupTests(unittest.TestCase):
    def invoke(self, product_id):
        event = {
            "pathParameters": {"productId": product_id},
            "requestContext": {"requestId": "test-request-123"},
            "headers": {"x-api-key": "do-not-log-this", "authorization": "secret-token"},
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = handler(event, None)
        return result, output.getvalue()

    def test_known_product_returns_json_product(self):
        result, _ = self.invoke("1738")
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["headers"]["Content-Type"], "application/json")
        self.assertEqual(json.loads(result["body"]), {
            "productId": "1738", "name": "Everyday Headphones",
            "price": 79.99, "currency": "USD",
        })

    def test_unknown_product_is_not_a_successful_empty_response(self):
        result, _ = self.invoke("9999")
        self.assertEqual(result["statusCode"], 404)
        self.assertEqual(json.loads(result["body"])["message"], "Product not found")

    def test_invalid_identifier_returns_client_error(self):
        for product_id in (None, "", "../1738", "headphones", "1234567890123"):
            with self.subTest(product_id=product_id):
                result, _ = self.invoke(product_id)
                self.assertEqual(result["statusCode"], 400)

    def test_missing_path_parameters_does_not_crash(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = handler({"pathParameters": None}, None)
        self.assertEqual(result["statusCode"], 400)

    def test_logs_correlate_request_without_exposing_headers(self):
        _, logs = self.invoke("1738")
        entry = json.loads(logs)
        self.assertEqual(entry["requestId"], "test-request-123")
        self.assertEqual(entry["status"], 200)
        self.assertNotIn("do-not-log-this", logs)
        self.assertNotIn("secret-token", logs)


if __name__ == "__main__":
    unittest.main()
