# Walmart Mexico

## Portal

- URL: `https://facturacion.walmartmexico.com.mx/Default.aspx`
- Production recipe: `vendors/walmart.py`
- CLI:
  ```bash
  python vendor_cli.py walmart --mode explore
  python vendor_cli.py walmart --mode dry-run --tr SAMPLE_TR --tc SAMPLE_TC --total 123.45 --date 2026-01-31
  ```

## Required Ticket Fields

- `tr`: Walmart ticket number.
- `tc`: Walmart transaction number.
- `total`: ticket total.
- `date`: purchase date in `YYYY-MM-DD`.
- Optional: `payment_method`.

## Known Flow

1. Open portal.
2. Close initial `Aceptar` dialog when present.
3. Click `Obtener factura`.
4. Fill RFC, postal code, TR, and TC.
5. Continue to fiscal data step.
6. Compare saved portal fiscal data against `.env`.
7. If values differ, Telegram asks whether to replace with `.env`, keep portal data, or cancel.
8. Select regimen, uso CFDI, and payment method when needed.
9. Enable email delivery, fill default email, and stop before `Facturar` in dry-run mode.
10. In live mode, click `Facturar` and wait for vendor-specific email confirmation.

## Success Evidence

Map to `SUCCESS_EMAIL` only when Walmart displays a clear sent-email message, currently expected as `FACTURA ENVIADA` or equivalent text containing `enviada`.

If the final action is triggered but no confirmation appears, map to `EMAIL_TRIGGERED_BUT_NO_CONFIRMATION`.

## Unverified / Watch Items

- Exact confirmation text should be revalidated with a live ticket after every portal change.
- Some placeholders include accents; the recipe keeps accented and non-accented fallback selectors.
- Ticket-gated steps cannot be fully verified in explore-only mode.
