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
        current_action = "Loading initial Walmart portal page"
        
        try:
            # 1. Click 'Aceptar' button to close the dialogue
            current_action = "Step 1: Handling initial dialogues (Aceptar)"
            self.handle_dialogues()

            # 2. Click the 'Obtener Factura' button to start the invoice process
            current_action = "Step 2: Clicking 'Obtener factura' button"
            btn_obtener = self.page.ele('text:Obtener factura', timeout=5) or self.page.ele('text:Obtener Factura', timeout=5)
            if btn_obtener:
                btn_obtener.click()
            
            # 3. Fill RFC, TC, TR, and zip code
            current_action = "Step 3a: Filling TR (Ticket) Number"
            if self.page.ele('#ctl00_ContentPlaceHolder1_txtTC', timeout=2):
                self.page.ele('#ctl00_ContentPlaceHolder1_txtTC').input(ticket_data.get('extra_data', {}).get('transaction_number', ''))
            
            current_action = "Step 3b: Filling TC (Transaction) Number"
            if self.page.ele('#ctl00_ContentPlaceHolder1_txtTR', timeout=2):
                self.page.ele('#ctl00_ContentPlaceHolder1_txtTR').input(ticket_data.get('extra_data', {}).get('web_id', ''))
            
            current_action = "Step 3c: Filling RFC"
            if self.page.ele('#ctl00_ContentPlaceHolder1_txtMemRFC', timeout=2):
                self.page.ele('#ctl00_ContentPlaceHolder1_txtMemRFC').input(self.fiscal_data['rfc'])
            
            # Zip Code (CP) - Always use the user's personal ZIP from .env for CFDI 4.0
            current_action = "Step 3d: Filling Zip Code (CP)"
            personal_zip = self.fiscal_data.get('zip', '')
            if self.page.ele('#ctl00_ContentPlaceHolder1_txtCP', timeout=2):
                self.page.ele('#ctl00_ContentPlaceHolder1_txtCP').input(personal_zip)
            
            # 4. Click 'Continuar' button
            current_action = "Step 4: Clicking 'Continuar' button"
            btn_continue = self.page.ele('text:Continuar', timeout=5) or self.page.ele('#btn_continue', timeout=5)
            if btn_continue:
                btn_continue.click()
            
            # 5. Handle Selects ('Regimen' and 'CFDI') and 'Razon Social'
            current_action = "Step 5a: Handling dialogues after Continuar"
            self.handle_dialogues()
            import constants
            
            # Fill Razon Social if it appears
            current_action = "Step 5b: Filling Razon Social"
            if self.page.ele('#ctl00_ContentPlaceHolder1_txtRazon', timeout=2):
                self.page.ele('#ctl00_ContentPlaceHolder1_txtRazon').input(self.fiscal_data['razon_social'])

            # Select Régimen Fiscal (e.g. 612)
            current_action = "Step 5c: Selecting Regimen Fiscal"
            if self.page.ele('#ctl00_ContentPlaceHolder1_ddlregimenFiscal', timeout=2):
                self.select_sat_option('#ctl00_ContentPlaceHolder1_ddlregimenFiscal', self.fiscal_data['regimen'], constants.REGIMEN_FISCAL)
            
            # Select Uso CFDI (e.g. G03)
            current_action = "Step 5d: Selecting Uso CFDI"
            if self.page.ele('#ctl00_ContentPlaceHolder1_ddlusoCFDI', timeout=2):
                self.select_sat_option('#ctl00_ContentPlaceHolder1_ddlusoCFDI', self.fiscal_data['uso_cfdi'], constants.USO_CFDI)
                
            # 6. Click 'Aceptar' button
            current_action = "Step 6: Clicking 'Aceptar' to confirm fiscal data"
            btn_aceptar = self.page.ele('text:Aceptar', timeout=5)
            if btn_aceptar:
                btn_aceptar.click()

            # 6.5 Handle dialogue to confirm if data is correct ('Aceptar' again)
            current_action = "Step 6.5: Handling confirm data dialogue (Aceptar)"
            self.handle_dialogues()

            # 7. Select Forma de Pago (Payment Method)
            current_action = "Step 7: Selecting Forma de Pago"
            payment_code = self.fiscal_data['forma_pago'] or ticket_data.get('extra_data', {}).get('payment_method', '01')
            if self.page.ele('#ctl00_ContentPlaceHolder1_ddlPaymentType', timeout=2):
                self.select_sat_option('#ctl00_ContentPlaceHolder1_ddlPaymentType', payment_code, constants.FORMA_PAGO)

            # 8. Click 'Continuar' button
            current_action = "Step 8: Clicking second 'Continuar' button"
            btn_continue_3 = self.page.ele('text:Continuar', timeout=5)
            if btn_continue_3:
                btn_continue_3.click()

            # 9. Email confirmation toggle and email box
            current_action = "Step 9a: Handling dialogues before email"
            self.handle_dialogues()
            
            current_action = "Step 9b: Toggling 'Enviar a correo electronico'"
            email_toggle = self.page.ele('@for=ctl00_ContentPlaceHolder1_rdCorreo', timeout=2) or self.page.ele('#ctl00_ContentPlaceHolder1_rdCorreo', timeout=2)
            if email_toggle:
                email_toggle.click()
            
            current_action = "Step 9c: Verifying/Filling Email Address"
            email_field = self.page.ele('#ctl00_ContentPlaceHolder1_txtEmail', timeout=2)
            if email_field:
                if email_field.value != self.default_email:
                    email_field.clear()
                    email_field.input(self.default_email)
            
            # 10. Click 'Facturar' button
            current_action = "Step 10: Clicking final 'Facturar' button"
            btn_facturar = self.page.ele('text:Facturar', timeout=5)
            if btn_facturar:
                btn_facturar.click()
            
            # 11. Verify specific Walmart success message
            current_action = "Step 11: Waiting for 'FACTURA ENVIADA' success message"
            self.handle_dialogues()
            if self.page.wait_for_ele('text:FACTURA ENVIADA', timeout=10):
                return "SUCCESS_EMAIL"
            else:
                return "EMAIL_TRIGGERED_BUT_NO_CONFIRMATION"
            
        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"walmart_error_{ticket_data.get('folio', 'unknown')}")
            return f"ERROR at [{current_action}]: {str(e)} (Screenshot saved: {screenshot_path})"
