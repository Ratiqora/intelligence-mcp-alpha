"""Exercise the workbench HTTP boundary with the installed Ratiqora Core."""

import http.client
import json
import threading
import unittest
from copy import deepcopy
from http.server import HTTPServer
from pathlib import Path
from secrets import token_urlsafe

from run import handler


class WorkbenchTest(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), None)
        self.server.timeout = 5
        self.port = self.server.server_port
        token = token_urlsafe(32)
        template = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
        self.server.RequestHandlerClass = handler(
            template.replace("__WORKBENCH_TOKEN__", token).encode("utf-8"), token, self.port
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join, 5)
        self.addCleanup(self.server.shutdown)
        self.headers = {
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Workbench-Token": token,
            "Content-Type": "application/json",
        }
        self.draft = {
            "question": "آیا باید زمان انتظار را تغییر دهیم؟",
            "finding": "Two reports show different outcomes.",
            "unknowns": "Test conditions vary.",
            "next": "Repeat the test under matched conditions.",
            "sources": [
                {"id": "S1", "kind": "synthetic_document", "reference": "Run A | page 2"},
                {"id": "S2", "kind": "public_document", "reference": "Public report B"},
            ],
            "observations": [
                {"text": "Upload failed.", "role": "supports", "source": "S1"},
                {"text": "<img src=x> [link](https://example.invalid)", "role": "challenges",
                 "source": "S2"},
            ],
        }

    def request(self, method, path, body=None, headers=None):
        with_header = self.headers if headers is None else headers
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body, headers=with_header)
            response = connection.getresponse()
            return response.status, response.getheader("Cache-Control"), response.read()
        finally:
            connection.close()

    def submit(self, draft, headers=None):
        status, _, body = self.request("POST", "/brief", json.dumps(draft), headers)
        return status, json.loads(body)

    def test_valid_and_repaired_references_export(self):
        status, result = self.submit(self.draft)
        self.assertEqual(status, 200)
        report = result["markdown"]
        self.assertIn(self.draft["question"], report)
        self.assertIn("| O1 | Supports the finding | Upload failed&#46; | S1 |", report)
        self.assertIn("| O2 | Challenges the finding |", report)
        self.assertIn("| S2 |", report)
        self.assertIn("S2 (Public citation): Public report B", report)
        self.assertIn("Run A &#124; page 2", report)
        self.assertNotIn("<img", report)
        self.assertNotIn("sha256:", report)
        self.draft["sources"].pop()
        status, result = self.submit(self.draft)
        self.assertEqual(status, 400)
        self.assertEqual(result, {"error": "Observation 2 points to a missing source."})
        self.draft["observations"][1]["source"] = "S1"
        status, result = self.submit(self.draft)
        self.assertEqual(status, 200)
        self.assertNotIn("S2", result["markdown"])

    def test_invalid_drafts_return_only_safe_error(self):
        cases = []
        duplicate = deepcopy(self.draft)
        duplicate["sources"][1]["id"] = "S1"
        cases.append(duplicate)
        blank = deepcopy(self.draft)
        blank["finding"] = " "
        cases.append(blank)
        invalid_role = deepcopy(self.draft)
        invalid_role["observations"][1]["role"] = "private-marker"
        cases.append(invalid_role)
        for draft in cases:
            with self.subTest():
                status, result = self.submit(draft)
                self.assertEqual(status, 400)
                self.assertEqual(result.keys(), {"error"})
                self.assertNotIn("Upload failed", result["error"])
                self.assertNotIn("private-marker", result["error"])

    def test_loopback_request_boundary_and_no_store(self):
        status, cache, body = self.request("GET", "/", headers={})
        self.assertEqual((status, cache), (200, "no-store"))
        self.assertIn(self.headers["X-Workbench-Token"].encode(), body)
        self.assertNotIn(b"__WORKBENCH_TOKEN__", body)
        for name, value in [
            ("Origin", "http://example.invalid"),
            ("X-Workbench-Token", "incorrect"),
            ("Host", "example.invalid"),
        ]:
            with self.subTest(name=name):
                headers = {**self.headers, name: value}
                self.assertEqual(self.submit(self.draft, headers)[0], 403)
        status, _, body = self.request("POST", "/brief", "{")
        self.assertEqual(status, 400)
        self.assertNotIn(b"markdown", body)
        status, _, _ = self.request(
            "POST", "/brief", "", {**self.headers, "Content-Length": "65537"}
        )
        self.assertEqual(status, 413)


if __name__ == "__main__":
    unittest.main()
