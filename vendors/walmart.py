from .base import BaseRecipe
import os

class WalmartRecipe(BaseRecipe):
    @property
    def url(self):
        return 'https://facturacion.walmartmexico.com.mx/'

    @property
    def selectors(self):
        return {
            "tr_input": "#tr_number",
            "tc_input": "#tc_number",
            "continue_button": "#btn_continue"
        }

    @property
    def ocr_hints(self):
        return (
            "For Walmart/Sam's Club/Bodega Aurrera: Look for a long 'Ticket' number (usually labeled as TR) "
            "and a 'Transaction' number (labeled as TC). "
            "The TR is often 20 digits, and the TC is 3-4 digits. "
            "Also look for 'Código Postal' or 'CP' (Zip Code)."
        )

    def run(self, ticket_data):
        self.page.get(self.url)
        
        try:
            # Walmart often has a landing page to choose 'Facturar'
            if self.page.ele('text:Facturar'):
                self.page.ele('text:Facturar').click()
            
            # Fill Ticket Details
            self.page.ele('#tr_number').input(ticket_data.get('extra_data', {}).get('transaction_number', ''))
            self.page.ele('#tc_number').input(ticket_data.get('extra_data', {}).get('web_id', ''))
            self.page.ele('#total').input(ticket_data['total'])
            self.page.ele('#rfc').input(self.fiscal_data['rfc'])
            
            # Zip Code (CP) - Always use the user's personal ZIP from .env for CFDI 4.0
            personal_zip = self.fiscal_data.get('zip', '')
            if self.page.ele('#cp_input'):
                self.page.ele('#cp_input').input(personal_zip)
            
            self.page.ele('#btn_continue').click()
            
            # Email-First Strategy
            # Walmart usually asks for email in the final step
            success = self.trigger_email('#email_input', '#btn_send_invoice')
            
            if success:
                return "SUCCESS_EMAIL"
            
            return "FAILED_EMAIL_TRIGGER"
            
        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"walmart_error_{ticket_data.get('folio', 'unknown')}")
            return f"ERROR: {str(e)} (Screenshot saved: {screenshot_path})"
