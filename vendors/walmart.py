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
            # 1. Click 'Aceptar' button to close the dialogue
            self.handle_dialogues()

            # 2. Click the 'Obtener Factura' button to start the invoice process
            btn_obtener = self.page.ele('text:Obtener factura', timeout=5) or self.page.ele('text:Obtener Factura', timeout=5)
            if btn_obtener:
                btn_obtener.click()
            
            # 3. Fill RFC, TC, TR, and zip code
            if self.page.ele('#tr_number', timeout=2):
                self.page.ele('#tr_number').input(ticket_data.get('extra_data', {}).get('transaction_number', ''))
            if self.page.ele('#tc_number', timeout=2):
                self.page.ele('#tc_number').input(ticket_data.get('extra_data', {}).get('web_id', ''))
            if self.page.ele('#rfc', timeout=2):
                self.page.ele('#rfc').input(self.fiscal_data['rfc'])
            
            # Zip Code (CP) - Always use the user's personal ZIP from .env for CFDI 4.0
            personal_zip = self.fiscal_data.get('zip', '')
            if self.page.ele('#cp_input', timeout=2):
                self.page.ele('#cp_input').input(personal_zip)
            
            # 4. Click 'Continuar' button
            btn_continue = self.page.ele('text:Continuar', timeout=5) or self.page.ele('#btn_continue', timeout=5)
            if btn_continue:
                btn_continue.click()
            
            # 5. Handle Selects ('Regimen' and 'CFDI')
            self.handle_dialogues()
            import constants
            
            # Select Régimen Fiscal (e.g. 612)
            if self.page.ele('#regimen_fiscal_select', timeout=2):
                self.select_sat_option('#regimen_fiscal_select', self.fiscal_data['regimen'], constants.REGIMEN_FISCAL)
            
            # Select Uso CFDI (e.g. G03)
            if self.page.ele('#uso_cfdi_select', timeout=2):
                self.select_sat_option('#uso_cfdi_select', self.fiscal_data['uso_cfdi'], constants.USO_CFDI)
                
            # Select Forma de Pago (Prioritize .env, fallback to ticket OCR) if it exists
            payment_code = self.fiscal_data['forma_pago'] or ticket_data.get('extra_data', {}).get('payment_method', '01')
            if self.page.ele('#forma_pago_select', timeout=2):
                self.select_sat_option('#forma_pago_select', payment_code, constants.FORMA_PAGO)

            # 6. Click 'Continuar' button again
            btn_continue_2 = self.page.ele('text:Continuar', timeout=5)
            if btn_continue_2:
                btn_continue_2.click()

            # 7. Asks if you want it by email and fill the email box
            self.handle_dialogues()
            email_field = self.page.ele('#email_input', timeout=2) or self.page.ele('@type=email', timeout=2)
            if email_field:
                if email_field.value != self.default_email:
                    email_field.clear()
                    email_field.input(self.default_email)
            
            # 8. Click 'Continuar' or 'Facturar' button
            btn_send = self.page.ele('text:Facturar', timeout=5) or self.page.ele('text:Continuar', timeout=5) or self.page.ele('#btn_send_invoice', timeout=5)
            if btn_send:
                btn_send.click()
            
            # 9. Verify specific Walmart success message
            if self.page.wait_for_ele('text:FACTURA ENVIADA', timeout=10):
                return "SUCCESS_EMAIL"
            else:
                return "EMAIL_TRIGGERED_BUT_NO_CONFIRMATION"
            
        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"walmart_error_{ticket_data.get('folio', 'unknown')}")
            return f"ERROR: {str(e)} (Screenshot saved: {screenshot_path})"
