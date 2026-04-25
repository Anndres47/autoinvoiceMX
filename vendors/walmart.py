from .base import BaseRecipe
import os

class WalmartRecipe(BaseRecipe):
    @property
    def url(self):
        return 'https://facturacion.walmartmexico.com.mx/Default.aspx'

    @property
    def selectors(self):
        return {
            "obtener_btn": "text:Obtener factura"
        }

    ocr_hints = (
        "For Walmart/Sam's Club/Bodega Aurrera: Look for a long 'Ticket' number (usually labeled as TR) "
        "and a 'Transaction' number (labeled as TC). "
        "The TR is often 20 digits, and the TC is 5 digits. "
        "Also look for 'Código Postal' or 'CP' (Zip Code)."
    )

    def run(self, ticket_data):
        import logging
        self.page.get(self.url)
        logging.info(f"Navigating to Walmart portal: {self.url}")
        current_action = "Loading Walmart portal page"
        
        try:
            # 1. Click 'Aceptar' button to close the initial dialogue
            current_action = "Step 1: Clicking initial 'Aceptar' button"
            logging.info(current_action)
            btn_aceptar_inicio = self.page.ele('text:Aceptar', timeout=5)
            if btn_aceptar_inicio:
                btn_aceptar_inicio.click()
            else:
                self.handle_dialogues() # Fallback to general handle_dialogues

            # 2. Click the 'Obtener Factura' link to start the invoice process
            current_action = "Step 2: Clicking 'Obtener factura' link"
            logging.info(current_action)
            btn_obtener = self.page.ele('text:Obtener factura', timeout=5)
            if btn_obtener:
                btn_obtener.click()
            
            # 3. Fill RFC, CP, TR, and TC using exact Playwright placeholders
            current_action = "Step 3a: Filling RFC"
            logging.info(current_action)
            rfc_box = self.page.ele('@placeholder=Membresía o RFC', timeout=10)
            if rfc_box:
                rfc_box.input(self.fiscal_data['rfc'])
            else:
                raise Exception("Could not find RFC input box.")
            
            current_action = "Step 3b: Filling Zip Code (CP)"
            logging.info(current_action)
            personal_zip = self.fiscal_data.get('zip', '')
            cp_box = self.page.ele('@placeholder=Código postal', timeout=5)
            if cp_box:
                cp_box.input(personal_zip)
            
            current_action = "Step 3c: Filling TR (Ticket) Number"
            logging.info(current_action)
            tr_val = ticket_data.get('extra_data', {}).get('tr') or ticket_data.get('extra_data', {}).get('transaction_number', '')
            tr_box = self.page.ele('@placeholder=Número de ticket', timeout=5)
            if tr_box:
                tr_box.input(tr_val)
            else:
                raise Exception("Could not find TR input box.")
            
            current_action = "Step 3d: Filling TC (Transaction) Number"
            logging.info(current_action)
            tc_val = ticket_data.get('extra_data', {}).get('tc') or ticket_data.get('extra_data', {}).get('web_id', '')
            tc_box = self.page.ele('@placeholder=# Transacción', timeout=5)
            if tc_box:
                tc_box.input(tc_val)
            else:
                raise Exception("Could not find TC input box.")
            
            # 4. Click 'Continuar' button
            current_action = "Step 4: Clicking 'Continuar' button"
            logging.info(current_action)
            btn_continue = self.page.ele('text:Continuar', timeout=5)
            if btn_continue:
                btn_continue.click()
            
            # VERIFY Step 4 worked by waiting for a Step 5 element
            if not self.page.ele('#ctl00_ContentPlaceHolder1_txtRazon', timeout=10):
                raise Exception("Failed to reach Step 5: Razon Social field not found. Likely validation error on Step 3.")
            
            # 5. Handle Selects ('Regimen' and 'CFDI'), 'Razon Social', and 'CP'
            current_action = "Step 5a: Handling dialogues after Continuar"
            logging.info(current_action)
            self.handle_dialogues()
            import constants
            
            current_action = "Step 5b: Checking and Filling Razon Social"
            logging.info(current_action)
            razon_field = self.page.ele('#ctl00_ContentPlaceHolder1_txtRazon', timeout=5)
            if razon_field:
                env_razon = self.fiscal_data['razon_social'].strip().upper()
                current_val = (razon_field.value or "").strip().upper()
                if env_razon != current_val:
                    logging.info(f"Overwriting pre-filled Razon Social: '{current_val}' -> '{env_razon}'")
                    razon_field.clear()
                    razon_field.input(env_razon)
                else:
                    logging.info("Razon Social is already correctly pre-filled.")

            current_action = "Step 5c: Checking and Filling Zip Code (txtCP)"
            logging.info(current_action)
            cp_field2 = self.page.ele('#ctl00_ContentPlaceHolder1_txtCP', timeout=2)
            if cp_field2:
                if cp_field2.value != personal_zip:
                    cp_field2.clear()
                    cp_field2.input(personal_zip)

            current_action = "Step 5d: Selecting Regimen Fiscal"
            logging.info(current_action)
            regimen_field = self.page.ele('#ctl00_ContentPlaceHolder1_ddlregimenFiscal', timeout=2)
            if regimen_field:
                if regimen_field.value in [None, "", "0"]:
                    logging.info("Selecting Regimen Fiscal from env")
                    self.select_sat_option('#ctl00_ContentPlaceHolder1_ddlregimenFiscal', self.fiscal_data['regimen'], constants.REGIMEN_FISCAL)
                else:
                    logging.info("Regimen Fiscal is pre-filled, skipping.")
            
            current_action = "Step 5e: Selecting Uso CFDI"
            logging.info(current_action)
            uso_field = self.page.ele('#ctl00_ContentPlaceHolder1_ddlusoCFDI', timeout=2)
            if uso_field:
                if uso_field.value in [None, "", "0"]:
                    logging.info("Selecting Uso CFDI from env")
                    self.select_sat_option('#ctl00_ContentPlaceHolder1_ddlusoCFDI', self.fiscal_data['uso_cfdi'], constants.USO_CFDI)
                else:
                    logging.info("Uso CFDI is pre-filled, skipping.")
                
            # 6. Click 'Aceptar' button
            current_action = "Step 6: Clicking 'Aceptar' to confirm fiscal data"
            logging.info(current_action)
            btn_aceptar = self.page.ele('text:Aceptar', timeout=5)
            if btn_aceptar:
                btn_aceptar.click()

            # 7. Handle dialogue to confirm if data is correct ('Continuar' according to Playwright trace)
            current_action = "Step 7: Clicking 'Continuar' on confirm data dialogue"
            logging.info(current_action)
            btn_continue_data = self.page.ele('text:Continuar', timeout=5)
            if btn_continue_data:
                btn_continue_data.click()
            else:
                self.handle_dialogues() # Fallback
            
            # VERIFY Step 7 worked by waiting for Step 8 element
            if not self.page.ele('#ctl00_ContentPlaceHolder1_ddlPaymentType', timeout=10):
                raise Exception("Failed to reach Payment step: Payment Type dropdown not found after confirmation.")

            # 8. Select Forma de Pago (Payment Method)
            current_action = "Step 8: Selecting Forma de Pago"
            logging.info(current_action)
            payment_code = self.fiscal_data['forma_pago'] or ticket_data.get('extra_data', {}).get('payment_method', '01')
            if self.page.ele('#ctl00_ContentPlaceHolder1_ddlPaymentType', timeout=2):
                self.select_sat_option('#ctl00_ContentPlaceHolder1_ddlPaymentType', payment_code, constants.FORMA_PAGO)

            # 9. Click 'Continuar' button
            current_action = "Step 9: Clicking 'Continuar' after payment method"
            logging.info(current_action)
            btn_continue_payment = self.page.ele('text:Continuar', timeout=5)
            if btn_continue_payment:
                btn_continue_payment.click()

            # 10. Email confirmation toggle and email box
            current_action = "Step 10a: Handling dialogues before email"
            logging.info(current_action)
            self.handle_dialogues()
            
            current_action = "Step 10b: Toggling 'Enviar a correo electronico'"
            logging.info(current_action)
            email_toggle = self.page.ele('text:Enviar a correo electrónico', timeout=5) or self.page.ele('@for=ctl00_ContentPlaceHolder1_rdCorreo', timeout=2)
            if email_toggle:
                email_toggle.click()
            
            current_action = "Step 10c: Verifying/Filling Email Address"
            logging.info(current_action)
            email_field = self.page.ele('@placeholder=Correo electrónico', timeout=5) or self.page.ele('#ctl00_ContentPlaceHolder1_txtEmail', timeout=2)
            if email_field:
                if email_field.value != self.default_email:
                    email_field.clear()
                    email_field.input(self.default_email)
            
            # 11. Click 'Facturar' button
            current_action = "Step 11: Clicking final 'Facturar' button"
            logging.info(current_action)
            btn_facturar = self.page.ele('text:Facturar', timeout=5)
            if btn_facturar:
                btn_facturar.click()
            
            # 12. Verify specific Walmart success message
            current_action = "Step 12: Waiting for 'FACTURA ENVIADA' success message"
            logging.info(current_action)
            self.handle_dialogues()
            if self.page.ele('text:FACTURA ENVIADA', timeout=15) or self.page.ele('text:enviada', timeout=15):
                logging.info("SUCCESS: Walmart invoice sent.")
                return "SUCCESS_EMAIL"
            else:
                logging.warning("WARNING: Email triggered but confirmation message not found.")
                return "EMAIL_TRIGGERED_BUT_NO_CONFIRMATION"
            
        except Exception as e:
            screenshot_path = self.save_debug_screenshot(f"walmart_error_{ticket_data.get('folio', 'unknown')}")
            return f"ERROR at [{current_action}]: {str(e)} (Screenshot saved: {screenshot_path})"
