# Vendor Learning Notes

Use this folder to keep the production recipe notes that come out of Codex CLI + Playwright MCP exploration.

Rules:

- Keep `.env.example` generic. Never paste real RFCs, emails, tokens, DB hosts, or ticket photos here.
- Use sanitized ticket values in examples.
- Record the vendor-specific success evidence before mapping it to `SUCCESS_EMAIL`.
- Mark ticket-gated steps as unverified when no valid ticket is available.
- Promote a vendor only after one live run confirms the invoice was sent by email.

Recommended learning flow:

1. Run explore-only mode to map the public portal flow:
   ```bash
   python vendor_cli.py walmart --mode explore
   ```
2. When a valid ticket exists, run dry-run mode and stop before final submit:
   ```bash
   python vendor_cli.py walmart --mode dry-run --tr SAMPLE_TR --tc SAMPLE_TC --total 123.45 --date 2026-01-31
   ```
3. After dry-run evidence is clean, run one live test:
   ```bash
   python vendor_cli.py walmart --mode live --tr REAL_TR --tc REAL_TC --total 123.45 --date 2026-01-31
   ```
