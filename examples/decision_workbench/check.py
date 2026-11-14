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
            "question": "Should we change the timeout?",
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

    def csv_request(self, body, headers=None):
        if headers is None:
            headers = {**self.headers, "Content-Type": "text/csv"}
        status, cache, result = self.request("POST", "/import-csv", body, headers)
        self.assertEqual(cache, "no-store")
        return status, json.loads(result)

    def test_import_groups_sources_and_generates_a_validated_brief(self):
        status, parsed = self.csv_request(
            b'\xef\xbb\xbfobservation,source_reference,source_type,role\r\n'
            b'"One upload failed, then retried","Run A, page 2",fictional,supports\r\n'
            b'"Another upload succeeded\r\non retry","Run A, page 2",fictional,challenges\r\n'
            b'"The queue was quiet","Run A, page 2",public,context\r\n'
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(parsed["sources"]), 2)
        self.assertEqual([row["source"] for row in parsed["observations"]], ["S1", "S1", "S2"])
        status, result = self.submit({**self.draft, **parsed})
        self.assertEqual(status, 200)
        report = result["markdown"]
        self.assertIn("Another upload succeeded on retry | S1", report)
        self.assertIn("S2 (Public citation): Run A, page 2", report)
        self.assertIn("Should we change the timeout?", report)

    def test_invalid_csv_never_returns_rows_or_echoes_input(self):
        header = b"observation,source_reference,source_type,role\n"
        row = b"private-marker,Run A,fictional,supports\n"
        invalid_cases = [
            row,
            header,
            header + b'"private-marker',
            header + row + b"Second entry,Run B,fictional,unknown\n",
            header + row * 13,
            header + b"\xff,Run A,fictional,context\n",
        ]
        for body in invalid_cases:
            with self.subTest():
                status, result = self.csv_request(body)
                self.assertEqual(status, 400)
                self.assertEqual(result.keys(), {"error"})
                self.assertNotIn("private-marker", result["error"])
        self.assertEqual(self.csv_request(header + row, self.headers)[0], 415)
        self.assertEqual(
            self.csv_request(
                header + row, {**self.headers, "Content-Type": "text/csv",
                               "Origin": "http://example.invalid"}
            )[0], 403
        )


if __name__ == "__main__":
    unittest.main()
