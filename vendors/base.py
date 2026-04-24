from DrissionPage import ChromiumPage, ChromiumOptions
import os
import abc

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
            "uso_cfdi": os.getenv("USO_CFDI")
        }

    @abc.abstractmethod
    def run(self, ticket_data):
        """Main entry point for the recipe."""
        pass

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

    def close(self):
        self.page.quit()
