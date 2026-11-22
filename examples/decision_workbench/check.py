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
            "hypothesis": "Every upload times out",
            "finding": "Keep the existing timeout",
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
        self.assertIn("| O1 | Supports the hypothesis | Upload failed. | S1 |", report)
        self.assertIn("| O2 | Challenges the hypothesis |", report)
        self.assertIn("| S2 |", report)
        self.assertIn("S2 (Public citation): Public report B", report)
        self.assertIn("Run A &#124; page 2", report)
        self.assertNotIn("<img", report)
        self.assertNotIn("sha256:", report)
        self.assertEqual(result["preview"]["observations"][1], {
            "id": "O2", "role": "challenges", "label": "Challenges the hypothesis",
            "summary": self.draft["observations"][1]["text"], "source": "S2",
        })
        self.assertEqual(result["preview"]["sources"][1]["id"], "S2")
        self.assertEqual(result["preview"]["sources"][1]["reference"], "Public report B")
        self.draft["sources"].pop()
        status, result = self.submit(self.draft)
        self.assertEqual(status, 400)
        self.assertEqual(result, {"error": "Observation 2 points to a missing source."})
        self.draft["observations"][1]["source"] = "S1"
        status, result = self.submit(self.draft)
        self.assertEqual(status, 200)
        self.assertNotIn("S2", result["markdown"])

    def test_markdown_prose_stays_readable_without_turning_input_into_markup(self):
        self.draft["next"] = "Re-test at 10:30. Keep [example](https://example.test) as text."
        status, result = self.submit(self.draft)
        self.assertEqual(status, 200)
        self.assertIn("Re-test at 10:30.", result["markdown"])
        self.assertNotIn("[example](", result["markdown"])
        self.assertNotIn("https://example.test", result["markdown"])

    def test_reopen_round_trip_preserves_authorship_and_rebuilds_report(self):
        self.draft["sources"][1]["id"] = "S9"
        self.draft["observations"][1]["source"] = "S9"
        status, generated = self.submit({**self.draft, "unrecognized": "discard this"})
        self.assertEqual(status, 200)
        saved = generated["editable"]
        self.assertEqual(saved, {"format": "ratiqora-decision-brief/v1", "brief": self.draft})
        status, cache, body = self.request("POST", "/open-brief", json.dumps({
            **saved, "preview": {"finding": "Unvalidated conclusion"}, "markdown": "Untrusted"
        }))
        self.assertEqual((status, cache), (200, "no-store"))
        self.assertEqual(json.loads(body), generated)

    def test_reopen_rejects_unsupported_files_and_broken_references(self):
        _, generated = self.submit(self.draft)
        invalid = deepcopy(generated["editable"])
        invalid["brief"]["observations"][0]["source"] = "S99"
        for data in (self.draft, {"format": "future", "brief": self.draft}, invalid):
            with self.subTest():
                status, _, body = self.request("POST", "/open-brief", json.dumps(data))
                self.assertEqual(status, 400)
                self.assertEqual(set(json.loads(body)), {"error"})
        status, _, _ = self.request("POST", "/open-brief", json.dumps(generated["editable"]), {})
        self.assertEqual(status, 403)

    def test_hypothesis_and_conclusion_stay_distinct(self):
        status, result = self.submit(self.draft)
        self.assertEqual(status, 200)
        for key, heading in [
            ("hypothesis", "Hypothesis under review"), ("finding", "Author’s conclusion")
        ]:
            self.assertEqual(result["preview"][key], self.draft[key])
            self.assertIn(f"## {heading}\n\n{self.draft[key]}\n", result["markdown"])
        revised = {**self.draft, "finding": "Investigate the retry first"}
        status, updated = self.submit(revised)
        self.assertEqual(status, 200)
        self.assertEqual(updated["preview"]["observations"], result["preview"]["observations"])
        self.assertEqual(updated["preview"]["hypothesis"], self.draft["hypothesis"])
        self.assertEqual(updated["preview"]["finding"], revised["finding"])

    def test_hypothesis_required_independently_of_conclusion(self):
        for value in [None, " ", "x" * 701]:
            draft = self.draft.copy()
            if value is None:
                draft.pop("hypothesis")
            else:
                draft["hypothesis"] = value
            with self.subTest(value_length=len(value or "")):
                status, result = self.submit(draft)
                self.assertEqual(status, 400)
                self.assertEqual(result, {
                    "error": "Hypothesis under review must contain 1–700 characters of text."
                })

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
                self.assertEqual(self.request("POST", "/brief", headers=headers)[0], 403)
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

    def test_multiline_source_keeps_word_boundaries(self):
        status, parsed = self.csv_request(
            b"observation,source_reference,source_type,role\r\n"
            b'Checkout resumed,"Fictional checkout report p2\r\nSection C",fictional,challenges\r\n'
        )
        self.assertEqual(status, 200)
        status, result = self.submit({**self.draft, **parsed})
        self.assertEqual(status, 200)
        self.assertEqual(
            result["preview"]["sources"][0]["reference"],
            "Fictional checkout report p2\r\nSection C",
        )
        self.assertIn("Fictional checkout report p2 Section C", result["markdown"])


if __name__ == "__main__":
    unittest.main()
