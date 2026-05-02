from .base import (
    BaseRecipe,
    CANCELLED_BY_USER,
    EMAIL_TRIGGERED_BUT_NO_CONFIRMATION,
    FAILED_EMAIL_TRIGGER,
    FISCAL_CANCEL,
    FISCAL_REPLACE_ENV,
    SUCCESS_EMAIL,
)

class OxxoRecipe(BaseRecipe):
    @property
    def url(self):
        return 'https://www4.oxxo.com:9443/facturacionElectronica-web/views/layout/inicio.do'

    @property
    def selectors(self):
        return {
            "folio_input": "@name=form:folio",
            "total_input": "@name=form:total",
            "next_button": "@name=form:continuar"
        }

    ocr_hints = (
        "For OXXO: Look for 'Folio-Venta' (usually 10MAY50...). "
        "The 'Total' is the grand total with tax. "
        "The 'Date' is near the top."
    )

    def run(self, ticket_data):
        if self.mode == "explore":
            return self.explore()

        # 1. Go to portal
        self.page.get(self.url)

        try:
            self.handle_dialogues()

            # 2. Fill the primary ticket data
            self.page.ele('@name=form:fecha_input').input(ticket_data['date'])
            self.page.ele('@name=form:folio').input(ticket_data['folio'])
            self.page.ele('@name=form:total').input(ticket_data['total'])
            self.page.ele('@name=form:continuar').click()

            self.handle_dialogues()

            # 3. Fill fiscal data, pausing if the portal already has conflicting data.
            rfc_field = self.page.ele('@name=form:rfc')
            razon_field = self.page.ele('@name=form:razon')
            zip_field = self.page.ele('@name=form:codigo')
            portal_values = {
                "rfc": self._field_value(rfc_field),
                "razon_social": self._field_value(razon_field),
                "zip": self._field_value(zip_field),
            }
            mismatches = self.build_fiscal_mismatches(portal_values)
            fiscal_choice = self.resolve_fiscal_mismatches("OXXO", mismatches)
            if fiscal_choice == FISCAL_CANCEL:
                return CANCELLED_BY_USER
            if fiscal_choice == FISCAL_REPLACE_ENV or not portal_values["rfc"]:
                rfc_field.clear()
                rfc_field.input(self.fiscal_data['rfc'])
            if fiscal_choice == FISCAL_REPLACE_ENV or not portal_values["razon_social"]:
                razon_field.clear()
                razon_field.input(self.fiscal_data['razon_social'])
            if fiscal_choice == FISCAL_REPLACE_ENV or not portal_values["zip"]:
                zip_field.clear()
                zip_field.input(self.fiscal_data['zip'])

            # 4. EMAIL-FIRST Strategy
            dry_run_result = self.maybe_stop_before_submit("oxxo")
            if dry_run_result:
                return dry_run_result

            email_success = self.trigger_email('@name=form:email', '@name=form:generarFactura')

            if email_success:
                if self.page.wait_for_ele('text:Factura generada', timeout=10) or self.page.wait_for_ele('text:enviada', timeout=10):
                    return SUCCESS_EMAIL
                return EMAIL_TRIGGERED_BUT_NO_CONFIRMATION

            return FAILED_EMAIL_TRIGGER

        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"oxxo_error_{ticket_data['folio']}")
            return f"ERROR: {str(e)} (Screenshot saved: {screenshot_path})"
