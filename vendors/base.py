from DrissionPage import ChromiumPage, ChromiumOptions
import os
import abc
import constants
import unicodedata

SUCCESS_EMAIL = "SUCCESS_EMAIL"
EMAIL_TRIGGERED_BUT_NO_CONFIRMATION = "EMAIL_TRIGGERED_BUT_NO_CONFIRMATION"
READY_TO_SUBMIT = "READY_TO_SUBMIT"
CANCELLED_BY_USER = "CANCELLED_BY_USER"
FAILED_EMAIL_TRIGGER = "FAILED_EMAIL_TRIGGER"

FISCAL_REPLACE_ENV = "replace_env"
FISCAL_KEEP_PORTAL = "keep_portal"
FISCAL_CANCEL = "cancel"

class BaseRecipe(abc.ABC):
    def __init__(self, headless=True, mode="live", fiscal_mismatch_resolver=None):
        self.mode = mode
        self.fiscal_mismatch_resolver = fiscal_mismatch_resolver
        self.options = ChromiumOptions()
        browser_path = os.getenv("BROWSER_PATH")
        if browser_path:
            self.options.set_browser_path(browser_path)
        if headless:
            self.options.headless()
            self.options.set_argument('--headless=new')

        # Crucial for Docker/Linux environments
        self.options.set_argument('--no-sandbox')
        self.options.set_argument('--disable-gpu')
        self.options.set_argument('--disable-dev-shm-usage')
        self.options.set_argument('--window-size=1920,1080')

        # Resource Optimization: Block images and CSS
        self.options.set_pref('profile.managed_default_content_settings.images', 2)
        # Note: Blocking CSS can sometimes break JS-heavy sites, 
        # but we'll try to keep it lean.
        # self.options.set_pref('profile.managed_default_content_settings.stylesheets', 2)

        self.page = ChromiumPage(self.options)
        self.default_email = os.getenv("DEFAULT_EMAIL")
        self.fiscal_data = {
            "rfc": os.getenv("RFC"),
            "razon_social": os.getenv("RAZON_SOCIAL"),
            "zip": os.getenv("POSTAL_CODE"),
            "regimen": os.getenv("REGIMEN_FISCAL"),
            "uso_cfdi": os.getenv("USO_CFDI"),
            "forma_pago": os.getenv("DEFAULT_FORMA_PAGO", "04")
        }

    def select_sat_option(self, selector, code, catalog):
        """
        Helper to select an option from a dropdown by matching a SAT code.
        Attempts to find by value (code) or by descriptive text.
        """
        try:
            dropdown = self.page.ele(selector)
            description = catalog.get(str(code), "")

            # Try selecting by value (code)
            if dropdown.select.by_value(str(code)):
                return True

            # Try selecting by text (description)
            if description and dropdown.select.by_text(description):
                return True

            # Fuzzy match by description if full text fails
            if description:
                normalized_description = self._normalize_text(description)
                for option in dropdown.select.options:
                    normalized_option = self._normalize_text(option.text)
                    if normalized_description in normalized_option:
                        option.click()
                        return True
            return False
        except Exception as e:
            print(f"Failed to select SAT option {code}: {e}")
            return False

    @staticmethod
    def _normalize_text(value):
        """Normalizes accents/case for resilient SAT dropdown matching."""
        text = unicodedata.normalize("NFKD", str(value))
        return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()

    @staticmethod
    def _field_value(field):
        """Returns a stable value from a DrissionPage element."""
        if not field:
            return ""
        value = getattr(field, "value", None)
        if value is None:
            value = getattr(field, "text", "")
        return str(value or "").strip()

    def _values_match(self, portal_value, expected_value):
        if not portal_value or not expected_value:
            return True
        return self._normalize_text(portal_value) == self._normalize_text(expected_value)

    def _expected_fiscal_values(self, key):
        expected = str(self.fiscal_data.get(key) or "").strip()
        values = [expected] if expected else []
        if key == "regimen" and expected in constants.REGIMEN_FISCAL:
            values.append(constants.REGIMEN_FISCAL[expected])
        if key == "uso_cfdi" and expected in constants.USO_CFDI:
            values.append(constants.USO_CFDI[expected])
        return values

    def build_fiscal_mismatches(self, portal_values):
        """
        Compares portal-saved fiscal data against .env fiscal data.
        Missing portal or env values are ignored because they do not prove a mismatch.
        """
        labels = {
            "rfc": "RFC",
            "razon_social": "Razon Social",
            "zip": "Postal Code",
            "regimen": "Regimen Fiscal",
            "uso_cfdi": "Uso CFDI",
        }
        mismatches = []
        for key, label in labels.items():
            portal_value = str(portal_values.get(key) or "").strip()
            expected_values = self._expected_fiscal_values(key)
            if portal_value and expected_values and not any(self._values_match(portal_value, expected) for expected in expected_values):
                mismatches.append({
                    "field": key,
                    "label": label,
                    "portal": portal_value,
                    "env": expected_values[0],
                })
        return mismatches

    def resolve_fiscal_mismatches(self, vendor, mismatches):
        """
        Asks the host app how to handle mismatched saved fiscal data.
        Defaults to keeping the portal values when no resolver is configured or it times out.
        """
        if not mismatches:
            return FISCAL_REPLACE_ENV
        if not self.fiscal_mismatch_resolver:
            print(f"Fiscal mismatch detected for {vendor}; keeping portal values by default.")
            return FISCAL_KEEP_PORTAL
        try:
            choice = self.fiscal_mismatch_resolver(vendor, mismatches)
            return choice or FISCAL_KEEP_PORTAL
        except Exception as e:
            print(f"Fiscal mismatch resolver failed: {e}. Keeping portal values.")
            return FISCAL_KEEP_PORTAL

    def maybe_stop_before_submit(self, name):
        """Stops dry-run mode before the irreversible portal submit action."""
        if self.mode == "dry-run":
            screenshot_path = self.save_debug_screenshot(f"{name}_ready_to_submit")
            return f"{READY_TO_SUBMIT} (Screenshot saved: {screenshot_path})"
        return None

    def explore(self):
        """Explore-only mode: open portal, handle initial dialogs, and capture evidence."""
        self.page.get(self.url)
        self.handle_dialogues()
        screenshot_path = self.save_debug_screenshot(f"{self.__class__.__name__.lower()}_explore")
        return f"EXPLORE_READY (Screenshot saved: {screenshot_path})"

    @abc.abstractproperty
    def url(self):
        """Returns the main URL for the billing portal."""
        pass

    @abc.abstractproperty
    def selectors(self):
        """Returns a dictionary of core selectors to check for health."""
        pass

    def check_health(self):
        """Verifies if the portal is reachable and core selectors are present."""
        try:
            self.page.get(self.url)
            missing = []
            for name, selector in self.selectors.items():
                if not self.page.ele(selector, timeout=5):
                    missing.append(name)
            
            if not missing:
                return True, "Healthy"
            return False, f"Broken selectors: {', '.join(missing)}"
        except Exception as e:
            return False, f"Portal unreachable: {str(e)}"

    @abc.abstractmethod
    def run(self, ticket_data):
        """Main entry point for the recipe."""
        pass

    def save_debug_screenshot(self, name="error_debug"):
        """Saves a screenshot to the storage/debug folder for remote debugging."""
        debug_dir = os.path.join("storage", "debug")
        os.makedirs(debug_dir, exist_ok=True)
        path = os.path.join(debug_dir, f"{name}.png")
        self.page.get_screenshot(path=path)
        print(f"Debug screenshot saved to: {path}")
        return path

    def trigger_email(self, email_field_selector, send_button_selector):
        """Generic method to fill email and send."""
        try:
            field = self.page.ele(email_field_selector)
            field.input(self.default_email)
            self.page.ele(send_button_selector).click()
            return True
        except Exception as e:
            print(f"Failed to trigger email: {e}")
            return False

    def handle_dialogues(self, wait_time=2):
        """Checks for common pop-ups, alerts or dialogues and closes them."""
        import time
        time.sleep(wait_time) # Short wait for JS modals to trigger
        try:
            # Handle JS alerts
            if self.page.handle_alert(accept=True):
                print("JS Alert accepted.")
            
            # Handle common modal close buttons
            close_selectors = [".close", "#close", "[aria-label='Close']", "text:Cerrar", "text:Aceptar"]
            for selector in close_selectors:
                btn = self.page.ele(selector, timeout=1)
                if btn:
                    try:
                        btn.click(by_js=True) # Use JS click in case it's covered by a backdrop
                        print(f"Closed dialogue using: {selector}")
                    except:
                        pass
        except:
            pass

    def close(self):
        self.page.quit()
