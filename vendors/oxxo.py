from .base import BaseRecipe

class OxxoRecipe(BaseRecipe):
    @property
    def url(self):
        return 'https://www4.oxxo.com:9443/facturacionElectronica-web/views/layout/inicio.do'

    @property
    def selectors(self):
        return {
            "folio_input": "#folio",
            "total_input": "#total",
            "next_button": "#btn_next"
        }

    @property
    def ocr_hints(self):
        return (
            "For OXXO: Look for 'Folio-Venta' (usually 10MAY50...). "
            "The 'Total' is the grand total with tax. "
            "The 'Date' is near the top."
        )

    def run(self, ticket_data):
        # 1. Go to portal
        self.page.get(self.url)
        
        # 2. Fill the primary ticket data
        # (These selectors are examples; you'd verify them in Step 2)
        try:
            self.page.ele('#folio').input(ticket_data['folio'])
            self.page.ele('#total').input(ticket_data['total'])
            self.page.ele('#fecha').input(ticket_data['date'])
            self.page.ele('#btn_next').click()
            
            # 3. Fill your Fiscal Data (automatically pulled from .env)
            self.page.ele('#rfc').input(self.fiscal_data['rfc'])
            self.page.ele('#razon_social').input(self.fiscal_data['razon_social'])
            
            # 4. EMAIL-FIRST Strategy
            # Use the helper from BaseRecipe
            email_success = self.trigger_email('#input_email', '#btn_send_email')
            
            if email_success:
                return "SUCCESS_EMAIL"
            
            return "FAILED_EMAIL_TRIGGER"
            
        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"oxxo_error_{ticket_data['folio']}")
            return f"ERROR: {str(e)} (Screenshot saved: {screenshot_path})"
