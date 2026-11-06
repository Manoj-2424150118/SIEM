"""Tests for the incident ledger and its wiring into the webhook.

Ledger tests are pure unit tests on temp files. The integration test
drives the real Flask app with subprocess mocked out: first webhook
blocks, second webhook for the same IP must be suppressed by the
ledger with zero additional firewall calls.
"""

import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from incident_ledger import IncidentLedger  # noqa: E402


class LedgerUnitTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "incidents.jsonl"
        self.ledger = IncidentLedger(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_record_and_recent_newest_first(self):
        self.ledger.record("203.0.113.1", "blocked")
        self.ledger.record("203.0.113.2", "aborted_safe", vt_score=0)
        recent = self.ledger.recent(10)
        self.assertEqual([r["ip"] for r in recent], ["203.0.113.2", "203.0.113.1"])
        self.assertEqual(recent[1]["action"], "blocked")

    def test_counts(self):
        self.ledger.record("203.0.113.1", "blocked")
        self.ledger.record("203.0.113.1", "skipped_duplicate")
        totals = self.ledger.counts()
        self.assertEqual(totals["blocked"], 1)
        self.assertEqual(totals["skipped_duplicate"], 1)
        self.assertEqual(totals["error"], 0)

    def test_was_blocked_within_window(self):
        self.ledger.record("198.51.100.7", "blocked")
        self.assertTrue(self.ledger.was_blocked_within("198.51.100.7", 24))
        self.assertFalse(self.ledger.was_blocked_within("198.51.100.8", 24))

    def test_window_expires_for_old_blocks(self):
        # Write a block with a backdated timestamp, then reload: the
        # index rebuilt from disk must treat it as outside the window.
        old = {
            "ts": "2020-01-01T00:00:00+00:00", "ip": "192.0.2.9",
            "action": "blocked", "vt_score": None, "detail": "",
        }
        self.path.write_text(json.dumps(old) + "\n", encoding="utf-8")
        reloaded = IncidentLedger(self.path)
        self.assertFalse(reloaded.was_blocked_within("192.0.2.9", 24))
        self.assertIsNotNone(reloaded.last_blocked_at("192.0.2.9"))

    def test_persistence_across_instances(self):
        self.ledger.record("203.0.113.55", "blocked")
        fresh = IncidentLedger(self.path)
        self.assertTrue(fresh.was_blocked_within("203.0.113.55", 24))
        self.assertEqual(fresh.counts()["blocked"], 1)

    def test_torn_line_is_tolerated(self):
        self.ledger.record("203.0.113.1", "blocked")
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write('{"ts": "truncated...\n')
        fresh = IncidentLedger(self.path)
        self.assertEqual(fresh.counts()["blocked"], 1)
        self.assertEqual(len(fresh.recent(5)), 1)

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            self.ledger.record("203.0.113.1", "nuked")


@unittest.skipUnless(platform.system() == "Linux", "integration flow uses the iptables branch")
class WebhookLedgerIntegrationTest(unittest.TestCase):
    """End-to-end through the Flask app with the firewall mocked."""

    @classmethod
    def setUpClass(cls):
        import webhook_listener
        cls.wl = webhook_listener
        cls.client = webhook_listener.app.test_client()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        fresh = IncidentLedger(Path(self._tmp.name) / "incidents.jsonl")
        self._ledger_patch = mock.patch.object(self.wl, "LEDGER", fresh)
        self._ledger_patch.start()
        self.addCleanup(self._ledger_patch.stop)
        self.addCleanup(self._tmp.cleanup)

    @staticmethod
    def _fake_run(cmd, **kwargs):
        # iptables -C check: report "rule absent" (rc=1); adds succeed.
        rc = 1 if "-C" in cmd else 0
        return subprocess.CompletedProcess(cmd, rc, stdout="", stderr="")

    def test_second_webhook_is_suppressed_by_ledger(self):
        headers = {"x-api-key": self.wl.API_KEY}
        env = {k: v for k, v in os.environ.items()
               if k not in ("VIRUSTOTAL_API_KEY", "DISCORD_WEBHOOK_URL",
                            "SLACK_WEBHOOK_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(self.wl.subprocess, "run", side_effect=self._fake_run) as run_mock, \
             mock.patch.object(self.wl.requests, "post") as post_mock:
            first = self.client.post("/webhook", json={"ip": "203.0.113.99"}, headers=headers)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.get_json()["status"], "success")
            calls_after_first = run_mock.call_count
            self.assertGreaterEqual(calls_after_first, 2)  # -C check + -A add

            second = self.client.post("/webhook", json={"ip": "203.0.113.99"}, headers=headers)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(second.get_json()["status"], "skipped")
            # The whole point: no new firewall work for the duplicate.
            self.assertEqual(run_mock.call_count, calls_after_first)
            post_mock.assert_not_called()  # and no second team alert

    def test_incidents_endpoint_requires_auth_and_reports(self):
        headers = {"x-api-key": self.wl.API_KEY}
        self.wl.LEDGER.record("203.0.113.5", "blocked", vt_score=12)
        denied = self.client.get("/incidents")
        self.assertEqual(denied.status_code, 401)
        ok = self.client.get("/incidents", headers=headers)
        self.assertEqual(ok.status_code, 200)
        body = ok.get_json()
        self.assertEqual(body["totals"]["blocked"], 1)
        self.assertEqual(body["incidents"][0]["ip"], "203.0.113.5")


if __name__ == "__main__":
    unittest.main()
