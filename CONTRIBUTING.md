# Contributing to SIEM

Thanks for helping improve this project! This repo is an automated
threat-hunting & incident-response pipeline: a Flask/Waitress **Active Defense
Node** (`webhook_listener.py`) that verifies webhook alerts against
VirusTotal, enforces blocks at the OS firewall, and records every decision in
an append-only JSONL incident ledger.

## Quick start

**Prerequisites:** Python 3.10+; Docker (only for the Elastic Stack);
Administrator (Windows) or root / `CAP_NET_ADMIN` (Linux) rights if you want
to exercise real firewall blocks.

```bash
git clone https://github.com/Manoj-2424150118/SIEM.git
cd SIEM
cp .env.example .env        # Windows: copy .env.example .env — then fill in your keys
pip install -r requirements.txt
pip install pytest
```

## Running the tests

```bash
python -m pytest tests/ -q
```

| Test file | Covers |
|---|---|
| `tests/test_webhook.py` | Webhook auth, IP validation, VirusTotal veto, block decisions, error paths |
| `tests/test_incident_ledger.py` | Ledger append/read, dedupe-window logic, torn-line tolerance, env config |
| `tests/test_attack.py` | Attack-simulator behaviour |

CI (**SIEM Pipeline Tests**) runs the same suite on every push/PR on
`windows-latest` with Python 3.10. Platform-dependent cases skip cleanly
where the OS or elevation isn't available — a skipped test is not a failure.
Please make sure `pytest` passes locally before opening a PR.

## Running the node locally

```bash
docker compose up -d        # Elasticsearch :9200, Kibana :5601 (optional — only for detection)
python webhook_listener.py  # Active Defense Node on :5001
```

Send a test event with `POST http://localhost:5001/webhook`, header
`x-api-key: <your WEBHOOK_API_KEY>`, body `{"ip": "203.0.113.10"}`. Use
`python attack_simulator.py` only against targets you own, and
`python stress_test.py` for concurrent-load checks.

## Ground rules

- **Never commit secrets.** All keys live in `.env`, which is git-ignored.
  `.env.example` documents key *names* only — copy it, never paste real
  values into it, into code, tests, or issues.
- **Security vulnerabilities: do not open a public issue.** See `SECURITY.md`
  — report via GitHub Private Vulnerability Reporting (repo → Security tab →
  Report a vulnerability).
- **Firewall changes need elevation**, and in an environment without it the
  node records an `error` decision instead of pretending the block happened.
  Don't bypass that behaviour in tests.
- Keep changes focused: one concern per PR, with tests for behaviour changes.
  Follow the existing code style and use clear, conventional commit messages
  (e.g. `fix(webhook): ...`, `test(ledger): ...`).
- The Elastic Stack compose file runs single-node with X-Pack security
  disabled — a local-lab configuration, not a production hardening guide.
  Don't present it as one.
