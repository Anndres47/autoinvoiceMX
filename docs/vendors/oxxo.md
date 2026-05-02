# OXXO

## Portal

- URL: `https://www4.oxxo.com:9443/facturacionElectronica-web/views/layout/inicio.do`
- Production recipe: `vendors/oxxo.py`
- CLI:
  ```bash
  python vendor_cli.py oxxo --mode explore
  python vendor_cli.py oxxo --mode dry-run --folio SAMPLE_FOLIO --total 123.45 --date 2026-01-31
  ```

## Required Ticket Fields

- `folio`: OXXO folio.
- `total`: ticket total.
- `date`: purchase date in `YYYY-MM-DD`.
- Optional: `payment_method`.

## Known Flow

1. Open portal.
2. Close common dialogs when present.
3. Fill date, folio, and total.
4. Continue to fiscal data step.
5. Compare any portal-saved fiscal fields against `.env`.
6. If values differ, Telegram asks whether to replace with `.env`, keep portal data, or cancel.
7. Fill missing fiscal fields from `.env`.
8. Stop before final invoice generation in dry-run mode.
9. In live mode, trigger email delivery and wait for vendor-specific confirmation.

## Success Evidence

Map to `SUCCESS_EMAIL` only when OXXO displays a clear generated/sent confirmation, currently expected as text containing `Factura generada` or `enviada`.

If the email trigger runs but confirmation is unclear, map to `EMAIL_TRIGGERED_BUT_NO_CONFIRMATION`.

## Unverified / Watch Items

- Date format accepted by the OXXO field should be validated with a real ticket.
- Ticket-gated steps cannot be fully verified in explore-only mode.
