from DrissionPage import ChromiumPage, ChromiumOptions
import os
import abc
import constants

class BaseRecipe(abc.ABC):
    def __init__(self, headless=True):
        self.options = ChromiumOptions()
        if headless:
            self.options.headless()

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
                for option in dropdown.select.options:
                    if description in option.text:
                        option.click()
                        return True
            return False
        except Exception as e:
            print(f"Failed to select SAT option {code}: {e}")
            return False

    @abc.abstractmethod

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

    @abc.abstractproperty
    def ocr_hints(self):
        """Returns a string with hints for Gemini on how to find data for this vendor."""
        pass

    def save_debug_screenshot(self, name="error_debug"):
        """Saves a screenshot to the storage folder for remote debugging."""
        path = os.path.join("storage", f"{name}.png")
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

    def handle_dialogues(self):
        """Checks for common pop-ups, alerts or dialogues and closes them."""
        try:
            # Handle JS alerts
            if self.page.handle_alert(accept=True):
                print("JS Alert accepted.")
            
            # Handle common modal close buttons
            close_selectors = [".close", "#close", "[aria-label='Close']", "text:Cerrar", "text:Aceptar"]
            for selector in close_selectors:
                btn = self.page.ele(selector, timeout=1)
                if btn:
                    btn.click()
                    print(f"Closed dialogue using: {selector}")
        except:
            pass

    def close(self):
        self.page.quit()
