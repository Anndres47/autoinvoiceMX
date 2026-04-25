from .base import BaseRecipe
import os

class WalmartRecipe(BaseRecipe):
    @property
    def url(self):
        return 'https://facturacion.walmartmexico.com.mx/'

    @property
    def selectors(self):
        return {
            "landing_btn": "text:Obtener factura"
        }

    ocr_hints = (
        "For Walmart/Sam's Club/Bodega Aurrera: Look for a long 'Ticket' number (usually labeled as TR) "
        "and a 'Transaction' number (labeled as TC). "
        "The TR is often 20 digits, and the TC is 3-4 digits. "
        "Also look for 'Código Postal' or 'CP' (Zip Code)."
    )

    def run(self, ticket_data):
        self.page.get(self.url)
        
        try:
            # Handle initial popups
            self.handle_dialogues()

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
            
            # Step 2: Corroborate info and handle Selects
            self.handle_dialogues()
            import constants
            
            # Select Régimen Fiscal (e.g. 612)
            if self.page.ele('#regimen_fiscal_select'):
                self.select_sat_option('#regimen_fiscal_select', self.fiscal_data['regimen'], constants.REGIMEN_FISCAL)
            
            # Select Uso CFDI (e.g. G03)
            if self.page.ele('#uso_cfdi_select'):
                self.select_sat_option('#uso_cfdi_select', self.fiscal_data['uso_cfdi'], constants.USO_CFDI)
                
            # Select Forma de Pago (Prioritize .env, fallback to ticket OCR)
            payment_code = self.fiscal_data['forma_pago'] or ticket_data.get('extra_data', {}).get('payment_method', '01')
            if self.page.ele('#forma_pago_select'):
                self.select_sat_option('#forma_pago_select', payment_code, constants.FORMA_PAGO)

            # Click 'Obtener Factura' to reach the final email stage
            if self.page.ele('text:Obtener Factura'):
                self.page.ele('text:Obtener Factura').click()

            # Email-First Strategy: Corroborate and Send
            self.handle_dialogues()
            email_field = self.page.ele('#email_input')
            if email_field and email_field.value != self.default_email:
                email_field.clear()
                email_field.input(self.default_email)
            
            success = self.trigger_email('#email_input', '#btn_send_invoice')
            
            # Verify specific Walmart success message
            if success:
                # Wait for the specific success text to appear on the page
                if self.page.wait_for_ele('text:FACTURA ENVIADA', timeout=10):
                    return "SUCCESS_EMAIL"
                else:
                    return "EMAIL_TRIGGERED_BUT_NO_CONFIRMATION"
            
            return "FAILED_EMAIL_TRIGGER"
            
        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"walmart_error_{ticket_data.get('folio', 'unknown')}")
            return f"ERROR: {str(e)} (Screenshot saved: {screenshot_path})"
