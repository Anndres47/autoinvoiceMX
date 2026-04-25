from DrissionPage import ChromiumPage, ChromiumOptions
import os
import abc
import constants

class BaseRecipe(abc.ABC):
    def __init__(self, headless=True):
        self.options = ChromiumOptions()
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
                for option in dropdown.select.options:
                    if description in option.text:
                        option.click()
                        return True
            return False
        except Exception as e:
            print(f"Failed to select SAT option {code}: {e}")
            return False

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
