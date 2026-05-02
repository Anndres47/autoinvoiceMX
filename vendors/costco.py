import re

from .base import (
    BaseRecipe,
    CANCELLED_BY_USER,
    EMAIL_TRIGGERED_BUT_NO_CONFIRMATION,
    FISCAL_CANCEL,
    FISCAL_KEEP_PORTAL,
    FISCAL_REPLACE_ENV,
    SUCCESS_EMAIL,
)


class CostcoRecipe(BaseRecipe):
    @property
    def url(self):
        return "https://www3.costco.com.mx/facturacion"

    @property
    def selectors(self):
        return {
            "generation_tab": "#ngb-nav-0",
            "ticket_input": "#ticket",
            "total_input": "#monto",
            "rfc_input": "#rfc",
            "continue_button": "text:Continuar",
        }

    ocr_hints = (
        "For Costco Mexico: use the Generacion tab. Extract the 'Ticket / Orden' number, "
        "which can be a 20-digit ticket/order value, and the 'Total pagado' amount. "
        "Costco ticket invoicing requires Ticket / Orden, Total pagado, and RFC. "
        "Membership-linked fiscal data may skip manual fiscal fields and show a final "
        "Solicitud de emision screen with a masked registered email."
    )

    def _page_text(self):
        try:
            body = self.page.ele("tag:body", timeout=2)
            return body.text if body else ""
        except Exception:
            return ""

    def _is_visible(self, element):
        try:
            is_displayed = element.states.is_displayed
            return bool(is_displayed() if callable(is_displayed) else is_displayed)
        except Exception:
            return True

    def _visible_element(self, selector, text=None, timeout=5):
        elements = self.page.eles(selector, timeout=timeout)
        for element in elements:
            if text and text not in (element.text or ""):
                continue
            if self._is_visible(element):
                return element
        return None

    def _masked_email_from_text(self, text):
        patterns = [
            r"correo\s+[\"']?\s*([^\"'\n\r]+@[^\"'\n\r\s]+)\s*[\"']?",
            r"([\w.+-]*[*xX]+[\w.+-]*@[\w.-]+\.\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text or "", flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _masked_email_matches(self, masked_email, expected_email):
        if not masked_email or not expected_email:
            return True
        compact_masked = re.sub(r"\s+", "", masked_email).casefold()
        compact_expected = re.sub(r"\s+", "", expected_email).casefold()
        if "@" in compact_masked:
            local_part, domain_part = compact_masked.split("@", 1)
            local_regex = "".join(".*" if ch == "*" else "." if ch == "x" else re.escape(ch) for ch in local_part)
            regex = f"^{local_regex}@{re.escape(domain_part)}$"
        else:
            regex = "^" + re.escape(compact_masked).replace(r"\*", ".*") + "$"
        return re.match(regex, compact_expected, flags=re.IGNORECASE) is not None

    def _redact_email(self, email):
        if not email or "@" not in email:
            return ""
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            safe_local = local[:1] + "***"
        else:
            safe_local = local[:1] + "***" + local[-1:]
        return f"{safe_local}@{domain}"

    def run(self, ticket_data):
        import logging

        if self.mode == "explore":
            return self.explore()

        current_action = "Loading Costco portal page"
        self.page.get(self.url)
        logging.info(f"Navigating to Costco portal: {self.url}")

        try:
            self.handle_dialogues(wait_time=1)

            current_action = "Step 1: Verifying Generacion tab"
            logging.info(current_action)
            generation_tab = self.page.ele("#ngb-nav-0", timeout=10)
            if not generation_tab:
                raise Exception("Generacion tab not found.")

            current_action = "Step 2a: Filling Ticket / Orden"
            logging.info(current_action)
            ticket_value = ticket_data.get("extra_data", {}).get("ticket_order") or ticket_data.get("folio")
            ticket_input = self.page.ele("#ticket", timeout=10)
            if not ticket_input:
                raise Exception("Ticket / Orden input not found.")
            ticket_input.clear()
            ticket_input.input(str(ticket_value))

            current_action = "Step 2b: Filling Total pagado"
            logging.info(current_action)
            total_input = self.page.ele("#monto", timeout=5)
            if not total_input:
                raise Exception("Total pagado input not found.")
            total_input.clear()
            total_input.input(str(ticket_data.get("total")))

            current_action = "Step 2c: Filling RFC"
            logging.info(current_action)
            rfc_input = self.page.ele("#rfc", timeout=5)
            if not rfc_input:
                raise Exception("RFC input not found.")
            rfc_input.clear()
            rfc_input.input(str(self.fiscal_data.get("rfc") or ""))

            current_action = "Step 3: Clicking Continuar to verify ticket"
            logging.info(current_action)
            continue_button = self._visible_element("#btnEnviar", text="Continuar", timeout=5) or self.page.ele("text:Continuar", timeout=2)
            if not continue_button:
                raise Exception("Continuar button not found.")
            continue_button.click()

            current_action = "Step 4: Waiting for final Solicitud de emision confirmation"
            logging.info(current_action)
            if not self.page.ele("text:Solicitud de", timeout=15):
                if self.page.ele("#razonSocial", timeout=2):
                    raise Exception("Portal requested manual fiscal data; this path is not verified for Costco yet.")
                raise Exception("Final solicitud confirmation was not reached after ticket verification.")

            page_text = self._page_text()
            masked_email = self._masked_email_from_text(page_text)
            if masked_email and not self._masked_email_matches(masked_email, self.default_email):
                mismatches = [{
                    "field": "email",
                    "label": "Email",
                    "portal": masked_email,
                    "env": self._redact_email(self.default_email),
                }]
                fiscal_choice = self.resolve_fiscal_mismatches("Costco", mismatches)
                logging.info(f"Fiscal/email mismatch choice for Costco: {fiscal_choice}")
                if fiscal_choice == FISCAL_CANCEL:
                    return CANCELLED_BY_USER
                if fiscal_choice == FISCAL_REPLACE_ENV:
                    raise Exception("Costco final confirmation does not expose an editable email field.")
                if fiscal_choice == FISCAL_KEEP_PORTAL:
                    logging.info("Keeping Costco portal-saved email.")

            current_action = "Step 5: Stopping before final Solicitar"
            logging.info(current_action)
            dry_run_result = self.maybe_stop_before_submit("costco")
            if dry_run_result:
                return dry_run_result

            current_action = "Step 6: Clicking final Solicitar button"
            logging.info(current_action)
            solicitar_button = self._visible_element("#btnEnviar", text="Solicitar", timeout=5)
            if not solicitar_button:
                raise Exception("Final Solicitar button not found.")
            solicitar_button.click()

            current_action = "Step 7: Waiting for Costco sent-email success evidence"
            logging.info(current_action)
            self.handle_dialogues(wait_time=1)
            success_selectors = [
                "text:se ha enviado",
                "text:ha sido enviado",
                "text:fue enviado",
                "text:factura enviada",
                "text:cfdi enviado",
                "text:éxito",
                "text:exito",
            ]
            for selector in success_selectors:
                if self.page.ele(selector, timeout=10):
                    page_text = self._page_text()
                    normalized = self._normalize_text(page_text)
                    if "envi" in normalized and "correo" in normalized and "sera enviado" not in normalized:
                        return SUCCESS_EMAIL

            return EMAIL_TRIGGERED_BUT_NO_CONFIRMATION

        except Exception as e:
            ticket_label = ticket_data.get("extra_data", {}).get("ticket_order") or ticket_data.get("folio", "unknown")
            screenshot_path = self.save_debug_screenshot(f"costco_error_{ticket_label}")
            return f"ERROR at [{current_action}]: {str(e)} (Screenshot saved: {screenshot_path})"
