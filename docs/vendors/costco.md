# Costco Mexico

## Portal

- URL: `https://www3.costco.com.mx/facturacion`
- Production recipe: `vendors/costco.py`
- CLI:
  ```bash
  python vendor_cli.py costco --mode explore
  python vendor_cli.py costco --mode dry-run --ticket-order SAMPLE_TICKET_ORDER --total 123.45
  ```

## Required Ticket Fields

- `ticket_order`: Costco `Ticket / Orden`; observed as a 20-digit value.
- `total`: `Total pagado`.
- RFC comes from `.env` as `RFC`.
- `date` is optional for this portal flow and kept only for history/OCR context when extracted.

Proposed `ticket_data.extra_data`:

```json
{
  "ticket_order": "string",
  "payment_method": "string or null"
}
```

## Selector Map

- Generacion tab: `#ngb-nav-0`
- Reenvio tab: `#ngb-nav-1`
- Ticket / Orden: `#ticket` / `input[name="ticket"]`
- Total pagado: `#monto` / `input[name="monto"]`
- RFC: `#rfc` / `input[name="rfc"]`
- Ticket help: `#showHelpTicket`
- Total help: `#showHelpMonto`
- Continue: visible text `Continuar`, button id `#btnEnviar`
- Clear/cancel: button id `#btnBorrar`
- Final irreversible submit: visible text `Solicitar`, button id `#btnEnviar`

Note: `#btnEnviar` and `#btnBorrar` are reused across hidden/visible steps. Prefer visible text when acting.

## Known Flow

1. Open `https://www3.costco.com.mx/facturacion`.
2. Confirm the `Generacion` tab is selected.
3. Fill `Ticket / Orden`, `Total pagado`, and RFC.
4. Click `Continuar`.
5. If the ticket matches a membership with saved fiscal data, Costco skips manual fiscal fields.
6. Portal shows `Solicitud de emision` and says the CFDI will use membership-registered data and be sent to a masked registered email.
7. Stop before `Solicitar` in dry-run mode.
8. In live mode, click `Solicitar`.
9. Wait for a clear sent-email success message.

## Fiscal Data Behavior

Observed ticket-gated behavior: Costco appears to invoice using tax data linked to the Costco membership for the matching ticket. Manual fields for `razonSocial`, `codigoPostal`, `regimenFiscal`, `usoCFDI`, `correo`, and `correoConfirmacion` exist in the DOM but were hidden in this successful membership-linked path.

The final confirmation only exposes a masked registered email. The recipe compares that masked pattern against `DEFAULT_EMAIL` when possible. If the masked email clearly differs, it pauses through the fiscal mismatch resolver. If the user chooses `REPLACE WITH ENV`, the recipe fails before submission because this Costco step does not expose an editable email field.

Mismatch handling defaults to `LEAVE AS PORTAL` if Telegram does not respond.

## Dry-Run Stopping Point

Stop at `Solicitud de emision`, before clicking the final `Solicitar` button.

`Solicitar` is the irreversible final invoice request.

## Success Evidence

Map to `SUCCESS_EMAIL` only when Costco displays a clear post-submit message indicating the CFDI/factura was sent to email.

If `Solicitar` is clicked but no clear sent-email confirmation appears, map to `EMAIL_TRIGGERED_BUT_NO_CONFIRMATION`.

## Unverified / Watch Items

- Manual fiscal-data entry path is unverified because the observed real ticket skipped it.
- Exact post-submit success text is unverified by dry run; user reported that clicking `Solicitar` displays the success email.
- Ticket validation error messages were not captured.
- Whether non-membership or mismatched-RFC tickets require membership number is unverified.

## DrissionPage Recipe Outline

1. Open portal and close common dialogs.
2. Locate `#ngb-nav-0`, `#ticket`, `#monto`, `#rfc`.
3. Fill ticket/order, total, and RFC from parsed ticket plus `.env`.
4. Click visible `Continuar`.
5. Wait for `Solicitud de emision`.
6. Extract masked email from page text and compare to `DEFAULT_EMAIL` using wildcard matching.
7. Stop in dry-run before visible `Solicitar`.
8. In live mode, click visible `Solicitar`.
9. Wait for sent-email confirmation and return `SUCCESS_EMAIL`; otherwise return `EMAIL_TRIGGERED_BUT_NO_CONFIRMATION`.
