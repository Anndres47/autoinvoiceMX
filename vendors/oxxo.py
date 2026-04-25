from .base import BaseRecipe

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

            # 3. Fill your Fiscal Data (automatically pulled from .env)
            self.page.ele('@name=form:rfc').input(self.fiscal_data['rfc'])
            self.page.ele('@name=form:razon').input(self.fiscal_data['razon_social'])
            self.page.ele('@name=form:codigo').input(self.fiscal_data['zip'])

            # 4. EMAIL-FIRST Strategy
            email_success = self.trigger_email('@name=form:email', '@name=form:generarFactura')

            if email_success:
                if self.page.wait_for_ele('text:Factura generada', timeout=10) or self.page.wait_for_ele('text:enviada', timeout=10):
                    return "SUCCESS_EMAIL"
                return "EMAIL_TRIGGERED_BUT_NO_CONFIRMATION"

            return "FAILED_EMAIL_TRIGGER"

        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"oxxo_error_{ticket_data['folio']}")
            return f"ERROR: {str(e)} (Screenshot saved: {screenshot_path})"
